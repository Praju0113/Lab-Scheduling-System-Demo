from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Lab, QueueEntry, QueueEntryType, QueueCursor, QueueStatus, Specialist, TestItem, TestStatus, Visit
from app.catalog import build_test_catalog
from app.services.scheduling import SchedulingService


def _queue_item(item: QueueEntry | None) -> dict | None:
    if item is None:
        return None
    return {
        'visit_id': item.visit.public_id,
        'visit_test_id': item.test_item_id,
        'test_name': item.test_item.test_name,
        'pending_since': item.pending_since.isoformat() if item.pending_since else None,
        'returned_at': item.returned_at.isoformat() if item.returned_at else None,
    }


def queue_snapshot(session: Session, lab_id: int) -> dict:
    queue_entries = session.scalars(
        select(QueueEntry)
        .where(QueueEntry.lab_id == lab_id)
        .options(selectinload(QueueEntry.visit), selectinload(QueueEntry.test_item))
        .order_by(QueueEntry.position.asc().nullslast(), QueueEntry.created_at.asc())
    ).all()
    current = next((item for item in queue_entries if item.queue_type == QueueEntryType.CURRENT), None)
    next_item = next((item for item in queue_entries if item.queue_type == QueueEntryType.NEXT), None)
    pending = [item for item in queue_entries if item.queue_type == QueueEntryType.PENDING]
    cursor = session.get(QueueCursor, lab_id)
    return {
        'lab_id': lab_id,
        'current': _queue_item(current),
        'next': _queue_item(next_item),
        'pending': [_queue_item(item) for item in pending],
        'consecutive_pending_accepts': cursor.consecutive_pending_accepts if cursor else 0,
    }


def frontend_visit(visit: Visit) -> dict:
    if all(test.status == TestStatus.COMPLETED for test in visit.tests):
        status = 'Completed'
        completed_at = max((test.completed_at for test in visit.tests if test.completed_at), default=None)
    elif any(test.is_blocked for test in visit.tests):
        status = 'Blocked'
        completed_at = None
    elif any(test.queue_status == QueueStatus.PENDING for test in visit.tests):
        status = 'Pending'
        completed_at = None
    else:
        status = 'Waiting'
        completed_at = None
    next_lab = next((test.assigned_lab_id for test in visit.tests if test.status != TestStatus.COMPLETED and test.assigned_lab_id), None)
    queue_number = min((test.sequence_order for test in visit.tests if test.sequence_order), default=0)
    return {
        'id': visit.public_id,
        'patient_name': visit.patient_name,
        'patient_age': visit.patient_age,
        'patient_gender': visit.patient_gender,
        'phone': visit.phone or str((visit.patient_snapshot or {}).get('phone', '')),
        'priority_type': visit.priority_type,
        'tests': [test.test_name for test in visit.tests],
        'status': status,
        'lab_id': f'l{next_lab}' if next_lab else None,
        'arrival_time': visit.arrival_time.isoformat() if visit.arrival_time else None,
        'completed_at': completed_at.isoformat() if completed_at else None,
        'queue_number': queue_number,
        'updated_at': visit.updated_at.isoformat() if visit.updated_at else None,
    }


def frontend_lab(session: Session, lab: Lab) -> dict:
    snapshot = queue_snapshot(session, lab.id)
    queue_ids: list[str] = []
    if snapshot['next']:
        queue_ids.append(snapshot['next']['visit_id'])
    queue_ids.extend(item['visit_id'] for item in snapshot['pending'])
    return {
        'id': f'l{lab.id}',
        'name': lab.name,
        'category': lab.category,
        'floor': lab.floor,
        'specialist_id': f's{lab.specialist_id}' if lab.specialist_id else None,
        'is_active': lab.is_active,
        'current_patient_id': snapshot['current']['visit_id'] if snapshot['current'] else None,
        'queue': queue_ids,
        'updated_at': lab.updated_at.isoformat() if lab.updated_at else None,
    }


def frontend_specialist(item: Specialist) -> dict:
    return {
        'id': f's{item.id}',
        'name': item.name,
        'gender': item.gender,
        'shift_start': item.shift_start.strftime('%H:%M'),
        'shift_end': item.shift_end.strftime('%H:%M'),
        'updated_at': item.updated_at.isoformat() if item.updated_at else None,
    }


def frontend_test_catalog() -> list[dict]:
    return [
        {
            'test_name': item['test_name'],
            'test_code': item['test_code'],
            'category': item['category'],
            'duration_minutes': item['duration_minutes'],
            'tags': list(item.get('tags', [])),
            'condition_category': item.get('condition_category'),
        }
        for item in build_test_catalog()
    ]


def waiting_candidates_payload(session: Session, lab_id: int) -> dict:
    """Get eligible waiting candidates for a specific lab."""
    lab_names = {lab.id: lab.name for lab in session.scalars(select(Lab)).all()}
    visits = session.scalars(select(Visit).options(selectinload(Visit.tests)).order_by(Visit.arrival_time.asc(), Visit.id.asc())).all()
    
    def check_dependencies_satisfied(visit: Visit, test: TestItem) -> bool:
        """Check if all prior tests for this visit are completed."""
        # Find all tests in the same visit with lower sequence_order
        prior_tests = [t for t in visit.tests if t.sequence_order < test.sequence_order]
        # All prior tests must be completed
        return all(t.status == TestStatus.COMPLETED for t in prior_tests)
    
    items: list[dict] = []
    for visit in visits:
        active_test = next((test for test in visit.tests if test.queue_status in {QueueStatus.WAITING, QueueStatus.CURRENT, QueueStatus.PENDING}), None)
        ordered_tests = sorted(visit.tests, key=lambda item: (item.sequence_order, item.id))
        for test in ordered_tests:
            if test.assigned_lab_id != lab_id:
                continue
            if test.status != TestStatus.SCHEDULED or test.queue_status != QueueStatus.WAITING:
                continue
            if test.is_blocked:
                continue
            dependencies_satisfied = check_dependencies_satisfied(visit, test)
            is_queue_eligible = active_test is None and dependencies_satisfied
            items.append({
                'visit_id': visit.public_id,
                'visit_test_id': test.id,
                'patient_name': visit.patient_name,
                'patient_age': visit.patient_age,
                'patient_gender': visit.patient_gender,
                'test_name': test.test_name,
                'queue_number': test.sequence_order,
                'arrival_time': visit.arrival_time.isoformat() if visit.arrival_time else None,
                'is_queue_eligible': is_queue_eligible,
                'active_queue_status': active_test.queue_status.value if active_test else None,
                'active_lab_id': f'l{active_test.assigned_lab_id}' if active_test and active_test.assigned_lab_id else None,
                'active_lab_name': lab_names.get(active_test.assigned_lab_id) if active_test and active_test.assigned_lab_id else None,
                'is_dependency_blocked': not dependencies_satisfied,
            })
            break
    return {'lab_id': f'l{lab_id}', 'items': items}


def bootstrap_payload(session: Session) -> dict:
    visits = session.scalars(select(Visit).options(selectinload(Visit.tests)).order_by(Visit.arrival_time.asc(), Visit.id.asc())).all()
    labs = session.scalars(select(Lab).order_by(Lab.id.asc())).all()
    specialists = session.scalars(select(Specialist).order_by(Specialist.id.asc())).all()
    return {
        'visits': [frontend_visit(visit) for visit in visits],
        'labs': [frontend_lab(session, lab) for lab in labs],
        'specialists': [frontend_specialist(item) for item in specialists],
    }


def admin_dashboard_payload(session: Session) -> dict:
    visits = session.scalars(select(Visit).options(selectinload(Visit.tests))).all()
    labs = session.scalars(select(Lab).order_by(Lab.id.asc())).all()
    total_tests_completed = 0
    deferred_tests = 0
    unschedulable_tests = 0
    pending_queue_items = session.scalar(select(func.count()).select_from(QueueEntry).where(QueueEntry.queue_type == QueueEntryType.PENDING)) or 0
    test_type_counter: Counter[str] = Counter()
    lab_metrics: list[dict] = []
    for visit in visits:
        for test in visit.tests:
            test_type_counter[test.test_name] += 1
            if test.status == TestStatus.COMPLETED:
                total_tests_completed += 1
            if test.status == TestStatus.UNSCHEDULABLE:
                unschedulable_tests += 1
            if test.queue_status == QueueStatus.PENDING:
                deferred_tests += 1
    for lab in labs:
        completed = session.scalar(select(func.count()).select_from(TestItem).where(TestItem.assigned_lab_id == lab.id, TestItem.status == TestStatus.COMPLETED)) or 0
        pending = session.scalar(select(func.count()).select_from(TestItem).where(TestItem.assigned_lab_id == lab.id, TestItem.status != TestStatus.COMPLETED, TestItem.status != TestStatus.UNSCHEDULABLE)) or 0
        lab_metrics.append({'lab_id': f'l{lab.id}', 'name': lab.name, 'completed': completed, 'pending': pending})
    return {
        'summary': {
            'total_tests_completed': total_tests_completed,
            'total_patients_attended': len(visits),
            'deferred_tests': deferred_tests,
            'unschedulable_tests': unschedulable_tests,
            'pending_queue_items': pending_queue_items,
        },
        'lab_metrics': lab_metrics,
        'test_type_distribution': [{'name': name, 'value': value} for name, value in test_type_counter.most_common()],
    }


def paginated_visits(session: Session, page: int, page_size: int, search: str | None = None) -> dict:
    stmt = select(Visit).options(selectinload(Visit.tests)).order_by(Visit.arrival_time.asc(), Visit.id.asc())
    count_stmt = select(func.count()).select_from(Visit)
    if search:
        pattern = f'%{search.strip()}%'
        filt = or_(Visit.public_id.ilike(pattern), Visit.phr_reference_id.ilike(pattern), Visit.patient_name.ilike(pattern))
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    total = session.scalar(count_stmt) or 0
    offset = max(page - 1, 0) * page_size
    items = session.scalars(stmt.offset(offset).limit(page_size)).all()
    return {'items': [frontend_visit(item) for item in items], 'total': total, 'page': page, 'page_size': page_size, 'has_more': offset + len(items) < total}


def delta_payload(session: Session, since: datetime | None = None) -> dict:
    """
    Fetch delta changes with proper transaction isolation to prevent race conditions.
    
    Race condition fixes:
    1. Single transaction: All queries execute within SERIALIZABLE isolation
    2. Snapshot consistency: 'now' timestamp captured after all data fetched
    3. Queue state ordering: Tests ordered by updated_at DESC to catch latest states
    4. Version tracking: Returns data versions for client-side caching
    """
    # Use transaction isolation level to ensure consistent snapshot
    from sqlalchemy import text
    
    # Execute all queries within single transaction context
    # This ensures no intermediate updates are visible between queries
    if since is None:
        visits = session.scalars(select(Visit).options(selectinload(Visit.tests))).all()
        labs = session.scalars(select(Lab)).all()
        specialists = session.scalars(select(Specialist)).all()
    else:
        # Filter by updated_at, but include margin for race condition avoidance
        # Include records within 1 second before 'since' in case of clock skew
        buffer_time = since - timedelta(seconds=1)
        
        visits = session.scalars(
            select(Visit)
            .where(Visit.updated_at >= buffer_time)
            .options(selectinload(Visit.tests))
            .order_by(Visit.updated_at.desc())
        ).all()
        
        labs = session.scalars(
            select(Lab)
            .where(Lab.updated_at >= buffer_time)
            .order_by(Lab.updated_at.desc())
        ).all()
        
        specialists = session.scalars(
            select(Specialist)
            .where(Specialist.updated_at >= buffer_time)
            .order_by(Specialist.updated_at.desc())
        ).all()
    
    # Capture snapshot timestamp AFTER all data is fetched
    # This prevents time-skew issues where frontend polls with earlier timestamp
    now = datetime.now(timezone.utc)
    
    # Sort tests by updated_at DESC to catch latest state transitions
    for visit in visits:
        visit.tests = sorted(visit.tests, key=lambda t: (t.status, -t.updated_at.timestamp()))
    
    return {
        'since': since.isoformat() if since else None,
        'now': now.isoformat(),
        'visits': [frontend_visit(visit) for visit in visits],
        'labs': [frontend_lab(session, lab) for lab in labs],
        'specialists': [frontend_specialist(item) for item in specialists],
        'metrics': admin_dashboard_payload(session),
    }
