from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CompletedTestSnapshot, QueueCursor, QueueEntry, QueueEntryType, QueueStatus, TestItem, TestStatus, Visit
from app.services.bootstrap import queue_snapshot
from app.services.patient_ids import patient_id_date


class QueueService:
    def __init__(self, session: Session, scheduler) -> None:
        self.session = session
        self.scheduler = scheduler

    def _get_cursor(self, lab_id: int) -> QueueCursor:
        cursor = self.session.get(QueueCursor, lab_id)
        if cursor is None:
            cursor = QueueCursor(lab_id=lab_id, consecutive_pending_accepts=0)
            self.session.add(cursor)
            self.session.flush()
        return cursor

    def _get_entry(self, lab_id: int, queue_type: QueueEntryType) -> QueueEntry | None:
        return self.session.scalar(select(QueueEntry).where(QueueEntry.lab_id == lab_id, QueueEntry.queue_type == queue_type).options(selectinload(QueueEntry.visit), selectinload(QueueEntry.test_item)))

    def _find_test(self, visit_test_id: int) -> tuple[Visit, TestItem]:
        test = self.session.scalar(select(TestItem).where(TestItem.id == visit_test_id).options(selectinload(TestItem.visit)))
        if test is None or test.visit is None:
            raise ValueError('Visit test not found')
        return test.visit, test

    def snapshot(self, lab_id: int) -> dict:
        return queue_snapshot(self.session, lab_id)

    def accept_current(self, lab_id: int) -> dict:
        cursor = self._get_cursor(lab_id)
        current = self._get_entry(lab_id, QueueEntryType.CURRENT)
        next_entry = self._get_entry(lab_id, QueueEntryType.NEXT)
        if current is None and next_entry is not None:
            next_entry.queue_type = QueueEntryType.CURRENT
            _, test = self._find_test(next_entry.test_item_id)
            test.status = TestStatus.IN_PROGRESS
            test.queue_status = QueueStatus.CURRENT
            cursor.consecutive_pending_accepts = 0
            self.session.flush()
            self.scheduler.refill_lab_queue(lab_id)
        self.session.flush()
        return self.snapshot(lab_id)

    def move_current_to_pending(self, lab_id: int) -> dict:
        current = self._get_entry(lab_id, QueueEntryType.CURRENT)
        next_entry = self._get_entry(lab_id, QueueEntryType.NEXT)
        source = current or next_entry
        if source is not None:
            source.queue_type = QueueEntryType.PENDING
            source.pending_since = datetime.now(timezone.utc)
            source.returned_at = None
            _, test = self._find_test(source.test_item_id)
            test.status = TestStatus.SCHEDULED
            test.queue_status = QueueStatus.PENDING
        self.scheduler.refill_lab_queue(lab_id)
        self.session.flush()
        return self.snapshot(lab_id)

    def accept_from_pending(self, lab_id: int, visit_test_id: int | None = None) -> dict:
        cursor = self._get_cursor(lab_id)
        if self._get_entry(lab_id, QueueEntryType.CURRENT) is not None:
            return self.snapshot(lab_id)
        pending_items = self.session.scalars(select(QueueEntry).where(QueueEntry.lab_id == lab_id, QueueEntry.queue_type == QueueEntryType.PENDING).options(selectinload(QueueEntry.visit), selectinload(QueueEntry.test_item)).order_by(QueueEntry.returned_at.asc().nullslast(), QueueEntry.pending_since.asc().nullslast(), QueueEntry.created_at.asc())).all()
        if not pending_items or cursor.consecutive_pending_accepts >= 2:
            return self.snapshot(lab_id)
        if visit_test_id is not None:
            selected = next((item for item in pending_items if item.test_item_id == visit_test_id), None)
            if selected is None:
                raise ValueError('Pending visit test not found')
            if selected.returned_at is None:
                selected.returned_at = datetime.now(timezone.utc)
        else:
            returned_items = [item for item in pending_items if item.returned_at is not None]
            selected = returned_items[0] if returned_items else pending_items[0]
        selected.queue_type = QueueEntryType.CURRENT
        _, test = self._find_test(selected.test_item_id)
        test.status = TestStatus.IN_PROGRESS
        test.queue_status = QueueStatus.CURRENT
        cursor.consecutive_pending_accepts += 1
        self.scheduler.refill_lab_queue(lab_id)
        self.session.flush()
        return self.snapshot(lab_id)

    def complete_current(self, lab_id: int) -> dict:
        current = self._get_entry(lab_id, QueueEntryType.CURRENT)
        if current is None:
            return self.snapshot(lab_id)
        visit, test = self._find_test(current.test_item_id)
        completed_at = datetime.now(timezone.utc)
        test.status = TestStatus.COMPLETED
        test.queue_status = QueueStatus.DONE
        test.completed_at = completed_at
        self.session.add(CompletedTestSnapshot(
            snapshot_date=patient_id_date(completed_at),
            patient_public_id=visit.public_id,
            patient_name=visit.patient_name,
            visit_id=visit.id,
            test_item_id=test.id,
            test_name=test.test_name,
            completed_at=completed_at,
            lab_id=current.lab_id,
            lab_name=current.lab.name if current.lab else None,
        ))
        self.session.delete(current)
        self.scheduler.rebuild_for_visit(visit.id, reason='dependency completion')
        self.scheduler.refill_lab_queue(lab_id)
        self.session.flush()
        return self.snapshot(lab_id)
