from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AssignmentHistory, Lab, QueueEntry, QueueEntryType, QueueStatus, TestItem, TestStatus, Visit


class SchedulingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _normalize(self, value: str | None) -> str:
        if not value:
            return ''
        return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()

    def _priority_score(self, visit: Visit, test: TestItem) -> int:
        score = 0
        if visit.priority_type.upper() == 'EMERGENCY':
            score += 1000
        now = datetime.now(visit.arrival_time.tzinfo)
        score += max(int((now - visit.arrival_time).total_seconds() // 60), 0)
        if 'FULL_BLADDER' in test.tags:
            score += 100
        if test.condition_category == 'Strict Fasting Blood':
            score += 80
        if 'PREFERRED_LAST' in test.tags:
            score -= 50
        return score

    def _movement_penalty(self, visit: Visit, lab: Lab, previous_floor: str | None) -> int:
        if previous_floor is None:
            return 0
        if visit.patient_age >= 50 or visit.patient_age < 2:
            return 100 if lab.floor != previous_floor else 0
        return 20 if lab.floor != previous_floor else 0

    def _requires_female_patient(self, test: TestItem) -> bool:
        labels = {self._normalize(test.category), self._normalize(test.condition_category), self._normalize(test.test_name), *(self._normalize(tag) for tag in test.tags)}
        return any(label in labels for label in {'pap smear test', 'mammography', 'female only'})

    def _requires_female_specialist(self, test: TestItem) -> bool:
        labels = {self._normalize(test.category), self._normalize(test.condition_category), self._normalize(test.test_name), *(self._normalize(tag) for tag in test.tags)}
        return any(label in labels for label in {'pap smear test', 'mammography', 'female specialist only'})

    def _slot_fits(self, visit: Visit, test: TestItem, lab: Lab) -> bool:
        specialist = lab.specialist
        if specialist is None or not specialist.is_active:
            return False
        if self._requires_female_patient(test) and visit.patient_gender.upper() != 'FEMALE':
            return False
        if self._requires_female_specialist(test) and specialist.gender.upper() != 'FEMALE':
            return False
        lab_open = visit.arrival_time.replace(hour=lab.opening_time.hour, minute=lab.opening_time.minute, second=0, microsecond=0)
        lab_close = visit.arrival_time.replace(hour=lab.closing_time.hour, minute=lab.closing_time.minute, second=0, microsecond=0)
        shift_start = visit.arrival_time.replace(hour=specialist.shift_start.hour, minute=specialist.shift_start.minute, second=0, microsecond=0)
        shift_end = visit.arrival_time.replace(hour=specialist.shift_end.hour, minute=specialist.shift_end.minute, second=0, microsecond=0)
        effective_start = max(datetime.now(visit.arrival_time.tzinfo), visit.arrival_time, lab_open, shift_start)
        effective_end = min(lab_close, shift_end)
        return effective_start + timedelta(minutes=test.duration_minutes + max(lab.cleanup_duration_minutes, 0)) <= effective_end

    def _candidate_labs(self, test: TestItem) -> list[Lab]:
        labels = {self._normalize(test.category), self._normalize(test.condition_category), self._normalize(test.test_name)}
        labels.discard('')
        labs = self.session.scalars(select(Lab).options(selectinload(Lab.specialist)).where(Lab.is_active.is_(True))).all()
        candidates = []
        for lab in labs:
            if lab.supported_test_codes:
                if test.test_code in lab.supported_test_codes:
                    candidates.append(lab)
                continue
            if self._normalize(lab.category) in labels:
                candidates.append(lab)
        return candidates

    def _lab_pressure(self, lab_id: int) -> int:
        entries = self.session.scalars(select(QueueEntry).where(QueueEntry.lab_id == lab_id)).all()
        pressure = 0
        for entry in entries:
            if entry.queue_type == QueueEntryType.CURRENT:
                pressure += 2
            else:
                pressure += 1
        return pressure

    def _best_lab(self, visit: Visit, test: TestItem, previous_floor: str | None) -> Lab | None:
        candidates = [lab for lab in self._candidate_labs(test) if self._slot_fits(visit, test, lab)]
        if not candidates:
            return None
        return min(candidates, key=lambda lab: (self._movement_penalty(visit, lab, previous_floor), self._lab_pressure(lab.id), lab.id))

    def _dependencies_satisfied(self, visit: Visit, test: TestItem) -> bool:
        code_map = {item.test_code: item for item in visit.tests}
        if test.test_code == 'TREADMILL_TEST_TMT':
            ecg = code_map.get('ELECTROCARDIOGRAM_ECG')
            if ecg and ecg.status != TestStatus.COMPLETED:
                return False
        if test.category == 'Urine Examination (Input Condition: Bladder needs to be full)':
            ultrasound = next((item for item in visit.tests if item.category == 'Ultrasound Scan'), None)
            if ultrasound and ultrasound.status != TestStatus.COMPLETED:
                return False
        return True

    def schedule_visit(self, visit_id: int, reason: str = 'visit scheduling') -> list[TestItem]:
        visit = self.session.scalar(select(Visit).where(Visit.id == visit_id).options(selectinload(Visit.tests)))
        if visit is None:
            return []
        ordered = sorted(visit.tests, key=lambda test: (-self._priority_score(visit, test), test.duration_minutes, test.id))
        previous_floor: str | None = None
        changed: list[TestItem] = []
        ultrasound_index = next((i for i, item in enumerate(ordered) if item.category == 'Ultrasound Scan'), None)
        urine_index = next((i for i, item in enumerate(ordered) if item.category == 'Urine Examination (Input Condition: Bladder needs to be full)'), None)
        if ultrasound_index is not None and urine_index is not None and ultrasound_index > urine_index:
            ultrasound = ordered.pop(ultrasound_index)
            ordered.insert(urine_index, ultrasound)
        for order, test in enumerate(ordered, start=1):
            test.sequence_order = order
            if test.status in {TestStatus.IN_PROGRESS, TestStatus.COMPLETED}:
                if test.assigned_lab:
                    previous_floor = test.assigned_lab.floor
                continue
            if test.queue_status in {QueueStatus.WAITING, QueueStatus.CURRENT, QueueStatus.PENDING} and test.assigned_lab_id:
                if test.assigned_lab:
                    previous_floor = test.assigned_lab.floor
                continue
            best_lab = self._best_lab(visit, test, previous_floor)
            previous_lab_id = test.assigned_lab_id
            test.caution_reason = None
            if best_lab is None:
                test.assigned_lab_id = None
                test.status = TestStatus.UNSCHEDULABLE
                test.queue_status = QueueStatus.NOT_QUEUED
                test.caution_reason = 'No eligible ACTIVE lab available for this test.'
                changed.append(test)
                continue
            if previous_lab_id != best_lab.id:
                self.session.add(AssignmentHistory(test_item_id=test.id, from_lab_id=previous_lab_id, to_lab_id=best_lab.id, reason=reason))
            test.assigned_lab_id = best_lab.id
            test.status = TestStatus.SCHEDULED
            if test.queue_status not in {QueueStatus.WAITING, QueueStatus.CURRENT, QueueStatus.PENDING, QueueStatus.DONE}:
                test.queue_status = QueueStatus.NOT_QUEUED
            previous_floor = best_lab.floor
            changed.append(test)
        self.session.flush()
        return changed

    def reschedule_for_lab(self, lab_id: int, reason: str = 'lab change') -> None:
        visit_ids = self.session.scalars(select(TestItem.visit_id).where(TestItem.assigned_lab_id == lab_id).distinct()).all()
        for visit_id in visit_ids:
            self.schedule_visit(visit_id, reason=reason)

    def reschedule_for_specialist(self, specialist_id: int, reason: str = 'specialist change') -> None:
        lab_ids = self.session.scalars(select(Lab.id).where(Lab.specialist_id == specialist_id)).all()
        for lab_id in lab_ids:
            self.reschedule_for_lab(lab_id, reason=reason)

    def refill_lab_queue(self, lab_id: int) -> None:
        existing_next = self.session.scalar(select(QueueEntry).where(QueueEntry.lab_id == lab_id, QueueEntry.queue_type == QueueEntryType.NEXT))
        if existing_next is not None:
            return
        visits = self.session.scalars(select(Visit).options(selectinload(Visit.tests)).order_by(Visit.arrival_time.asc(), Visit.id.asc())).all()
        for visit in visits:
            has_active = any(test.queue_status in {QueueStatus.WAITING, QueueStatus.CURRENT, QueueStatus.PENDING} for test in visit.tests)
            if has_active:
                continue
            candidate = next((test for test in sorted(visit.tests, key=lambda item: (item.sequence_order, item.id)) if test.assigned_lab_id == lab_id and test.status == TestStatus.SCHEDULED and test.queue_status == QueueStatus.NOT_QUEUED and self._dependencies_satisfied(visit, test)), None)
            if candidate:
                candidate.queue_status = QueueStatus.WAITING
                self.session.add(QueueEntry(lab_id=lab_id, visit_id=visit.id, test_item_id=candidate.id, queue_type=QueueEntryType.NEXT))
                self.session.flush()
                return

    def refill_all_queues(self) -> None:
        for lab_id in self.session.scalars(select(Lab.id).order_by(Lab.id.asc())).all():
            self.refill_lab_queue(lab_id)

    def schedule_all(self) -> None:
        for visit_id in self.session.scalars(select(Visit.id).order_by(Visit.id.asc())).all():
            self.schedule_visit(visit_id, reason='full scheduling run')
        self.refill_all_queues()

    def rebuild_for_visit(self, visit_id: int, reason: str = 'visit changed') -> None:
        self.schedule_visit(visit_id, reason=reason)
        self.refill_all_queues()
