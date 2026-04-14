from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import Base, SessionLocal, engine, get_db
from app.models import Lab, QueueEntry, QueueStatus, Specialist, TestItem, TestStatus, Visit
from app.realtime import emit_nowait, mount
from app.schemas import AcceptPendingPayload, DeltaResponse, FrontendPatientPayload, LabPayload, SpecialistPayload, VisitListResponse, VisitPayload
from app.seed import reset_database, seed_database
from app.catalog import test_catalog_map
from app.services.bootstrap import admin_dashboard_payload, bootstrap_payload, delta_payload, frontend_lab, frontend_specialist, frontend_test_catalog, frontend_visit, paginated_visits, waiting_candidates_payload
from app.services.patient_ids import build_patient_id, extract_sequence, patient_id_date
from app.services.queue import QueueService
from app.services.scheduling import SchedulingService
from app.services.or_scheduler import ORScheduler
from app.services.planning_poker import PlanningPokerService, VotingStatus

app = FastAPI(title='Scalable Lab Scheduling Backend')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'] if settings.allow_all_cors_origins else list(settings.cors_origins),
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def _ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE visits ADD COLUMN IF NOT EXISTS phone VARCHAR(20)"))
        connection.execute(text("ALTER TABLE test_items ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE NOT NULL"))


@app.on_event('startup')
def startup() -> None:
    _ensure_schema()
    with SessionLocal() as session:
        if settings.reset_db_on_startup:
            reset_database(session)
        # Seeding disabled - use manual seed endpoints only
        # if settings.seed_on_startup:
        #     seed_database(session)
        #     or_scheduler = ORScheduler(session)
        #     or_scheduler.run_optimization()
        #     session.commit()


def _next_public_id(db: Session, arrival_time: datetime) -> str:
    local_arrival = arrival_time.astimezone() if arrival_time.tzinfo else arrival_time
    visit_date = patient_id_date(local_arrival)
    start_of_day = local_arrival.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    existing_ids = db.scalars(
        select(Visit.public_id)
        .where(Visit.arrival_time >= start_of_day, Visit.arrival_time < end_of_day)
        .order_by(Visit.id.asc())
    ).all()
    sequences = [seq for public_id in existing_ids if (seq := extract_sequence(public_id, visit_date)) is not None]
    sequence = (max(sequences) + 1) if sequences else 0
    return build_patient_id(visit_date, sequence)


def _apply_frontend_patient_payload(db: Session, visit: Visit, payload: FrontendPatientPayload, reason: str) -> Visit:
    if not payload.test_names:
        raise HTTPException(status_code=400, detail='At least one test is required')
    catalog = test_catalog_map()
    invalid_tests = [name for name in payload.test_names if name not in catalog]
    if invalid_tests:
        raise HTTPException(status_code=400, detail=f'Unknown tests: {", ".join(invalid_tests)}')

    visit.patient_name = payload.patient_name
    visit.patient_age = payload.patient_age
    visit.patient_gender = payload.patient_gender
    visit.priority_type = payload.priority_type
    visit.phone = payload.phone or None
    visit.patient_snapshot = {**(visit.patient_snapshot or {}), 'phone': payload.phone}

    preserved_tests: list[TestItem] = []
    editable_tests: list[TestItem] = []
    for test in visit.tests:
        if test.status in {TestStatus.COMPLETED, TestStatus.IN_PROGRESS} or test.queue_status in {QueueStatus.WAITING, QueueStatus.CURRENT, QueueStatus.PENDING}:
            preserved_tests.append(test)
        else:
            editable_tests.append(test)

    remaining_requested = Counter(payload.test_names)
    for test in preserved_tests:
        if remaining_requested[test.test_name] > 0:
            remaining_requested[test.test_name] -= 1

    for test in editable_tests:
        if remaining_requested[test.test_name] > 0:
            item = catalog[test.test_name]
            test.test_code = item['test_code']
            test.category = item['category']
            test.duration_minutes = int(item['duration_minutes'])
            test.tags = list(item.get('tags', []))
            test.condition_category = item.get('condition_category')
            remaining_requested[test.test_name] -= 1
            continue
        queue_entries = db.scalars(select(QueueEntry).where(QueueEntry.test_item_id == test.id)).all()
        for entry in queue_entries:
            db.delete(entry)
        db.delete(test)

    db.flush()

    for test_name, count in remaining_requested.items():
        if count <= 0:
            continue
        item = catalog[test_name]
        for _ in range(count):
            db.add(TestItem(
                visit_id=visit.id,
                test_code=item['test_code'],
                test_name=item['test_name'],
                category=item['category'],
                duration_minutes=int(item['duration_minutes']),
                tags=list(item.get('tags', [])),
                condition_category=item.get('condition_category'),
            ))

    db.flush()
    # Note: OR optimization is triggered by the caller after this function returns
    refreshed = db.scalar(select(Visit).where(Visit.id == visit.id).options(selectinload(Visit.tests)))
    return refreshed or visit


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/api/frontend/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    return bootstrap_payload(db)


@app.get('/api/frontend/admin-dashboard')
def admin_dashboard(db: Session = Depends(get_db)):
    return admin_dashboard_payload(db)


@app.get('/api/frontend/test-catalog')
def frontend_test_catalog_route():
    return {'items': frontend_test_catalog()}


@app.post('/api/frontend/patients')
async def create_frontend_patient(payload: FrontendPatientPayload, db: Session = Depends(get_db)):
    if not payload.test_names:
        raise HTTPException(status_code=400, detail='At least one test is required')
    catalog = test_catalog_map()
    invalid_tests = [name for name in payload.test_names if name not in catalog]
    if invalid_tests:
        raise HTTPException(status_code=400, detail=f'Unknown tests: {", ".join(invalid_tests)}')
    now = datetime.now().astimezone()
    visit = Visit(
        public_id=_next_public_id(db, now),
        phr_reference_id=f'PHR-MANUAL-{now.strftime("%Y%m%d%H%M%S%f")}',
        patient_name=payload.patient_name,
        patient_age=payload.patient_age,
        patient_gender=payload.patient_gender,
        priority_type=payload.priority_type,
        phone=payload.phone or None,
        arrival_time=now,
        patient_snapshot={'phone': payload.phone},
    )
    db.add(visit)
    db.flush()
    for test_name in payload.test_names:
        item = catalog[test_name]
        from app.models import TestStatus, QueueStatus
        # Tests created in WAITING state - ready for OR scheduling
        db.add(TestItem(
            visit_id=visit.id,
            test_code=item['test_code'],
            test_name=item['test_name'],
            category=item['category'],
            duration_minutes=int(item['duration_minutes']),
            tags=list(item.get('tags', [])),
            condition_category=item.get('condition_category'),
            status=TestStatus.SCHEDULED,
            queue_status=QueueStatus.WAITING,
        ))
    db.flush()
    # CRITICAL FIX: Use ORScheduler instead of deprecated SchedulingService
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    response = frontend_visit(visit)
    visit = db.scalar(select(Visit).where(Visit.id == visit.id).options(selectinload(Visit.tests))) or visit
    response = frontend_visit(visit)
    emit_nowait('visit.updated', response)
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return response


@app.patch('/api/frontend/patients/{visit_public_id}')
async def update_frontend_patient(visit_public_id: str, payload: FrontendPatientPayload, db: Session = Depends(get_db)):
    visit = db.scalar(select(Visit).where(Visit.public_id == visit_public_id).options(selectinload(Visit.tests)))
    if visit is None:
        raise HTTPException(status_code=404, detail='Patient visit not found')
    visit = _apply_frontend_patient_payload(db, visit, payload, reason='frontend patient updated')
    db.commit()
    # Trigger OR optimization to re-assign any new tests
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    response = frontend_visit(visit)
    emit_nowait('visit.updated', response)
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return response


@app.get('/api/visits', response_model=VisitListResponse)
def list_visits(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=200), search: str | None = None, db: Session = Depends(get_db)):
    return paginated_visits(db, page=page, page_size=page_size, search=search)


@app.get('/api/frontend/delta', response_model=DeltaResponse)
def frontend_delta(since: datetime | None = None, db: Session = Depends(get_db)):
    return delta_payload(db, since=since)


@app.post('/api/specialists')
async def create_specialist(payload: SpecialistPayload, db: Session = Depends(get_db)):
    specialist = Specialist(name=payload.name, gender=payload.gender, shift_start=datetime.strptime(payload.shift_start[:5], '%H:%M').time(), shift_end=datetime.strptime(payload.shift_end[:5], '%H:%M').time(), is_active=payload.is_active)
    db.add(specialist)
    db.flush()
    db.commit()
    response = frontend_specialist(specialist)
    emit_nowait('specialist.updated', response)
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return response


@app.patch('/api/specialists/{specialist_id}')
async def update_specialist(specialist_id: int, payload: SpecialistPayload, db: Session = Depends(get_db)):
    specialist = db.get(Specialist, specialist_id)
    if specialist is None:
        raise HTTPException(status_code=404, detail='Specialist not found')
    specialist.name = payload.name
    specialist.gender = payload.gender
    specialist.shift_start = datetime.strptime(payload.shift_start[:5], '%H:%M').time()
    specialist.shift_end = datetime.strptime(payload.shift_end[:5], '%H:%M').time()
    specialist.is_active = payload.is_active
    db.commit()
    # Trigger OR optimization to re-assign based on new specialist availability
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    response = frontend_specialist(specialist)
    emit_nowait('specialist.updated', response)
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return response


@app.delete('/api/specialists/{specialist_id}')
async def delete_specialist(specialist_id: int, db: Session = Depends(get_db)):
    specialist = db.get(Specialist, specialist_id)
    if specialist is None:
        raise HTTPException(status_code=404, detail='Specialist not found')
    db.delete(specialist)
    db.commit()
    emit_nowait('specialist.updated', {'id': f's{specialist_id}', 'deleted': True})
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return {'message': 'Specialist deleted'}


@app.post('/api/labs')
async def create_lab(payload: LabPayload, db: Session = Depends(get_db)):
    lab = Lab(
        name=payload.name,
        category=payload.category,
        floor=payload.floor,
        room_number=payload.room_number,
        opening_time=datetime.strptime((payload.opening_time or '07:00:00')[:8], '%H:%M:%S').time(),
        closing_time=datetime.strptime((payload.closing_time or '19:00:00')[:8], '%H:%M:%S').time(),
        cleanup_duration_minutes=payload.cleanup_duration_minutes,
        is_active=payload.is_active,
        specialist_id=payload.specialist_id,
        supported_test_codes=[],
    )
    db.add(lab)
    db.flush()
    # Trigger OR optimization to re-assign tests based on new lab availability
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    response = frontend_lab(db, lab)
    emit_nowait('lab.updated', response)
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return response


@app.patch('/api/labs/{lab_id}')
async def update_lab(lab_id: int, payload: LabPayload, db: Session = Depends(get_db)):
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail='Lab not found')
    lab.name = payload.name
    lab.category = payload.category
    lab.floor = payload.floor
    lab.room_number = payload.room_number
    lab.is_active = payload.is_active
    lab.specialist_id = payload.specialist_id
    lab.cleanup_duration_minutes = payload.cleanup_duration_minutes
    if payload.opening_time:
        lab.opening_time = datetime.strptime(payload.opening_time[:8], '%H:%M:%S').time()
    if payload.closing_time:
        lab.closing_time = datetime.strptime(payload.closing_time[:8], '%H:%M:%S').time()
    db.commit()
    # Trigger OR optimization to re-assign based on updated lab configuration
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    response = frontend_lab(db, lab)
    emit_nowait('lab.updated', response)
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return response


@app.delete('/api/labs/{lab_id}')
async def delete_lab(lab_id: int, db: Session = Depends(get_db)):
    from app.models import TestStatus, QueueStatus
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail='Lab not found')
    affected_tests = db.scalars(select(TestItem).where(TestItem.assigned_lab_id == lab_id, TestItem.status != TestStatus.COMPLETED)).all()
    for test in affected_tests:
        test.assigned_lab_id = None
        test.status = TestStatus.UNSCHEDULABLE
        test.queue_status = QueueStatus.NOT_QUEUED
        test.caution_reason = 'Assigned lab was deleted.'
    db.delete(lab)
    # Use ORScheduler instead of deprecated SchedulingService
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    emit_nowait('lab.updated', {'id': f'l{lab_id}', 'deleted': True})
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return {'message': 'Lab deleted'}


@app.get('/api/labs/{lab_id}/waiting-candidates')
def waiting_candidates(lab_id: int, db: Session = Depends(get_db)):
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail='Lab not found')
    return waiting_candidates_payload(db, lab_id)


@app.get('/api/queues/{lab_id}')
def get_queue(lab_id: int, db: Session = Depends(get_db)):
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail='Lab queue not found')
    return QueueService(db, SchedulingService(db)).snapshot(lab_id)


@app.post('/api/queues/{lab_id}/accept-current')
async def accept_current(lab_id: int, db: Session = Depends(get_db)):
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail='Lab queue not found')
    snapshot = QueueService(db, SchedulingService(db)).accept_current(lab_id)
    db.commit()
    emit_nowait('queue.updated', {'labId': f'l{lab_id}', 'snapshot': snapshot})
    return snapshot


@app.post('/api/queues/{lab_id}/move-current-to-pending')
async def move_current_to_pending(lab_id: int, db: Session = Depends(get_db)):
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail='Lab queue not found')
    snapshot = QueueService(db, SchedulingService(db)).move_current_to_pending(lab_id)
    db.commit()
    emit_nowait('queue.updated', {'labId': f'l{lab_id}', 'snapshot': snapshot})
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return snapshot


@app.post('/api/queues/{lab_id}/accept-from-pending')
async def accept_from_pending(lab_id: int, payload: AcceptPendingPayload | None = None, db: Session = Depends(get_db)):
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail='Lab queue not found')
    try:
        snapshot = QueueService(db, SchedulingService(db)).accept_from_pending(lab_id, payload.visit_test_id if payload else None)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    emit_nowait('queue.updated', {'labId': f'l{lab_id}', 'snapshot': snapshot})
    return snapshot


@app.post('/api/queues/{lab_id}/complete-current')
async def complete_current(lab_id: int, db: Session = Depends(get_db)):
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail='Lab queue not found')
    snapshot = QueueService(db, SchedulingService(db)).complete_current(lab_id)
    db.commit()
    # Trigger OR optimization to schedule next tests
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    emit_nowait('queue.updated', {'labId': f'l{lab_id}', 'snapshot': snapshot})
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return snapshot


@app.post('/api/phr-sync/patients')
async def phr_sync_patients(payload: list[VisitPayload], db: Session = Depends(get_db)):
    created: list[str] = []
    for item in payload:
        snapshot = dict(item.patient_snapshot)
        if item.phone:
            snapshot['phone'] = item.phone
        visit = Visit(
            public_id=_next_public_id(db, item.arrival_time),
            phr_reference_id=item.phr_reference_id,
            patient_name=item.patient_name,
            patient_age=item.patient_age,
            patient_gender=item.patient_gender,
            priority_type=item.priority_type,
            phone=item.phone or snapshot.get('phone'),
            arrival_time=item.arrival_time,
            patient_snapshot=snapshot,
        )
        db.add(visit)
        db.flush()
        for test_payload in item.tests:
            from app.models import TestStatus, QueueStatus
            db.add(TestItem(
                visit_id=visit.id,
                test_code=test_payload['test_code'],
                test_name=test_payload['test_name'],
                category=test_payload['category'],
                duration_minutes=int(test_payload.get('duration_minutes', 10)),
                tags=list(test_payload.get('tags', [])),
                condition_category=test_payload.get('condition_category'),
                status=TestStatus.SCHEDULED,
                queue_status=QueueStatus.WAITING,
            ))
        db.flush()
        created.append(visit.public_id)
    db.commit()
    # Use OR-Scheduler for all patients
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    emit_nowait('visit.updated', {'created': created})
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return {'created': created}


@app.post('/api/scheduling/run')
async def run_scheduling(db: Session = Depends(get_db)):
    or_scheduler = ORScheduler(db)
    result = or_scheduler.run_optimization()
    db.commit()
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return {'message': 'Scheduling refreshed', 'result': result}


# ===== OR Scheduler Endpoints =====
@app.post('/api/or/optimize')
async def run_or_optimization(db: Session = Depends(get_db)):
    """Run OR-Tools optimization to assign tests to labs."""
    or_scheduler = ORScheduler(db)
    result = or_scheduler.run_optimization()
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return result


@app.get('/api/or/schedule-preview')
async def get_or_schedule_preview(db: Session = Depends(get_db)):
    """Preview optimal assignments without applying them."""
    or_scheduler = ORScheduler(db)
    assignments = or_scheduler.optimize_schedule()
    return {
        'assignments_count': len(assignments),
        'assignments': assignments,
        'timestamp': datetime.now().isoformat()
    }


# ===== Planning Poker Endpoints =====
@app.post('/api/planning-poker/sessions')
async def create_poker_session(
    item_type: str,
    item_id: str,
    item_name: str,
    description: str = '',
    db: Session = Depends(get_db)
):
    """Create a new Planning Poker estimation session."""
    service = PlanningPokerService(db)
    session = service.create_session(item_type, item_id, item_name, description)
    return {
        'session_id': session.id,
        'item_type': session.item_type,
        'item_name': session.item_name,
        'status': session.status,
        'fibonacci_sequence': service.FIBONACCI_SEQUENCE
    }


@app.get('/api/planning-poker/sessions')
async def list_poker_sessions(status: VotingStatus | None = None):
    """List all Planning Poker sessions."""
    sessions = PlanningPokerService.list_sessions(status)
    return [
        {
            'session_id': s.id,
            'item_type': s.item_type,
            'item_name': s.item_name,
            'status': s.status,
            'participants': len(s.votes),
            'created_at': s.created_at.isoformat()
        }
        for s in sessions
    ]


@app.post('/api/planning-poker/sessions/{session_id}/join')
async def join_poker_session(session_id: str, user_id: str, username: str, db: Session = Depends(get_db)):
    """Join a Planning Poker session."""
    service = PlanningPokerService(db)
    try:
        session = service.join_session(session_id, user_id, username)
        return {
            'session_id': session.id,
            'status': session.status,
            'participants': [
                {'user_id': v.user_id, 'username': v.username, 'voted': v.value is not None}
                for v in session.votes.values()
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post('/api/planning-poker/sessions/{session_id}/vote')
async def cast_poker_vote(session_id: str, user_id: str, value: int, db: Session = Depends(get_db)):
    """Cast a vote in a Planning Poker session."""
    service = PlanningPokerService(db)
    try:
        session = service.cast_vote(session_id, user_id, value)
        return {
            'session_id': session.id,
            'your_vote': value,
            'total_votes': len([v for v in session.votes.values() if v.value is not None]),
            'total_participants': len(session.votes)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post('/api/planning-poker/sessions/{session_id}/reveal')
async def reveal_poker_votes(session_id: str, db: Session = Depends(get_db)):
    """Reveal all votes in a Planning Poker session."""
    service = PlanningPokerService(db)
    try:
        session = service.reveal_votes(session_id)
        votes = [v.value for v in session.votes.values() if v.value is not None]
        return {
            'session_id': session.id,
            'votes': [
                {'username': v.username, 'value': v.value}
                for v in session.votes.values()
            ],
            'stats': service.get_session_stats(session_id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post('/api/planning-poker/sessions/{session_id}/complete')
async def complete_poker_session(session_id: str, db: Session = Depends(get_db)):
    """Complete a Planning Poker session and calculate consensus."""
    service = PlanningPokerService(db)
    try:
        session = service.complete_session(session_id)
        return {
            'session_id': session.id,
            'status': session.status,
            'final_value': session.final_value,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get('/api/planning-poker/sessions/{session_id}/stats')
async def get_poker_session_stats(session_id: str, db: Session = Depends(get_db)):
    """Get statistics for a Planning Poker session."""
    service = PlanningPokerService(db)
    try:
        return service.get_session_stats(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# RE-INTEGRATED: REACT UI ENDPOINTS
# ==========================================

@app.get('/api/lobby/next')
def get_next_patients(db: Session = Depends(get_db)):
    """Get patients waiting for next test assignment (lobby optimization candidates)."""
    from app.models import TestItem, TestStatus, QueueStatus
    # Run OR optimization to ensure queue is up-to-date
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    # Return tests that are waiting for assignment
    waiting_tests = db.scalars(
        select(TestItem)
        .where(
            TestItem.status == TestStatus.SCHEDULED,
            TestItem.queue_status == QueueStatus.WAITING
        )
        .options(selectinload(TestItem.visit))
    ).all()
    return [
        {
            'test_id': t.id,
            'test_name': t.test_name,
            'test_code': t.test_code,
            'visit_id': t.visit_id,
            'patient_name': t.visit.patient_name,
            'patient_id': t.visit.public_id,
            'assigned_lab_id': t.assigned_lab_id,
            'status': t.queue_status.value
        }
        for t in waiting_tests
    ]


@app.get('/api/lobby/pending')
def get_pending_patients(db: Session = Depends(get_db)):
    """Get patients in pending state (paused/blocked tests)."""
    from app.models import TestItem, QueueStatus
    pending_tests = db.scalars(
        select(TestItem)
        .where(TestItem.queue_status == QueueStatus.PENDING)
        .options(selectinload(TestItem.visit))
    ).all()
    return [
        {
            'test_id': t.id,
            'test_name': t.test_name,
            'test_code': t.test_code,
            'visit_id': t.visit_id,
            'patient_name': t.visit.patient_name,
            'patient_id': t.visit.public_id,
            'assigned_lab_id': t.assigned_lab_id,
            'status': t.queue_status.value
        }
        for t in pending_tests
    ]


@app.get('/api/labs/{lab_id}/current')
def get_current_patient_in_lab(lab_id: int, db: Session = Depends(get_db)):
    """Get the patient currently being processed in a lab."""
    from app.models import TestItem, QueueStatus
    test = db.scalar(
        select(TestItem)
        .where(
            TestItem.assigned_lab_id == lab_id,
            TestItem.queue_status == QueueStatus.CURRENT
        )
        .options(selectinload(TestItem.visit))
    )
    if not test:
        raise HTTPException(status_code=404, detail='No patient currently in this lab')
    return {
        'test_id': test.id,
        'test_name': test.test_name,
        'test_code': test.test_code,
        'visit_id': test.visit_id,
        'patient_name': test.visit.patient_name,
        'patient_id': test.visit.public_id,
        'status': test.queue_status.value
    }


@app.post('/api/tests/{test_id}/start')
def start_test(test_id: int, db: Session = Depends(get_db)):
    """Mark a test as in-progress (specialist started working on it)."""
    from app.models import TestItem, TestStatus, QueueStatus
    test = db.get(TestItem, test_id)
    if not test:
        raise HTTPException(status_code=404, detail='Test not found')
    test.status = TestStatus.IN_PROGRESS
    test.queue_status = QueueStatus.CURRENT
    db.commit()
    return {
        'test_id': test.id,
        'status': test.status.value,
        'queue_status': test.queue_status.value
    }


@app.post('/api/tests/{test_id}/complete')
def complete_test(test_id: int, db: Session = Depends(get_db)):
    """Mark a test as completed."""
    from app.models import TestItem, TestStatus, QueueStatus, CompletedTestSnapshot
    from datetime import datetime, timezone
    from app.services.patient_ids import patient_id_date

    test = db.scalar(
        select(TestItem).where(TestItem.id == test_id).options(selectinload(TestItem.visit))
    )
    if not test:
        raise HTTPException(status_code=404, detail='Test not found')

    completed_at = datetime.now(timezone.utc)
    test.status = TestStatus.COMPLETED
    test.queue_status = QueueStatus.DONE
    test.completed_at = completed_at

    # Create snapshot record
    db.add(CompletedTestSnapshot(
        snapshot_date=patient_id_date(completed_at),
        patient_public_id=test.visit.public_id,
        patient_name=test.visit.patient_name,
        visit_id=test.visit.id,
        test_item_id=test.id,
        test_name=test.test_name,
        completed_at=completed_at,
        lab_id=test.assigned_lab_id,
        lab_name=test.assigned_lab.name if test.assigned_lab else None,
    ))

    # Delete any existing queue entry
    queue_entry = db.scalar(select(QueueEntry).where(QueueEntry.test_item_id == test_id))
    if queue_entry:
        db.delete(queue_entry)

    db.commit()
    return {
        'test_id': test.id,
        'status': test.status.value,
        'queue_status': test.queue_status.value,
        'completed_at': completed_at.isoformat()
    }


@app.post('/api/tests/{test_id}/unblock')
def unblock_test(test_id: int, db: Session = Depends(get_db)):
    """Unblock a test and return it to NOT_QUEUED so OR-Solver can route it."""
    from app.models import TestItem, TestStatus, QueueStatus
    test = db.get(TestItem, test_id)
    if not test:
        raise HTTPException(status_code=404, detail='Test not found')

    test.status = TestStatus.SCHEDULED
    # CRITICAL FIX: Changed from WAITING to NOT_QUEUED
    test.queue_status = QueueStatus.NOT_QUEUED
    test.caution_reason = None
    db.commit()

    # Run OR optimization to re-assign
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()

    return {
        'test_id': test.id,
        'status': test.status.value,
        'queue_status': test.queue_status.value
    }


@app.post('/api/tests/{test_id}/pending')
def specialist_push_to_pending(test_id: int, db: Session = Depends(get_db)):
    """Push a test to pending state (specialist needs patient to wait)."""
    from app.models import TestItem, TestStatus, QueueStatus, QueueEntry, QueueEntryType
    from datetime import datetime, timezone

    test = db.get(TestItem, test_id)
    if not test:
        raise HTTPException(status_code=404, detail='Test not found')

    test.status = TestStatus.SCHEDULED
    test.queue_status = QueueStatus.PENDING

    # Update or create queue entry
    queue_entry = db.scalar(select(QueueEntry).where(QueueEntry.test_item_id == test_id))
    if queue_entry:
        queue_entry.queue_type = QueueEntryType.PENDING
        queue_entry.pending_since = datetime.now(timezone.utc)
    else:
        db.add(QueueEntry(
            test_item_id=test_id,
            visit_id=test.visit_id,
            lab_id=test.assigned_lab_id,
            queue_type=QueueEntryType.PENDING,
            pending_since=datetime.now(timezone.utc)
        ))

    db.commit()
    return {
        'test_id': test.id,
        'status': test.status.value,
        'queue_status': test.queue_status.value
    }


@app.post('/api/visits/{visit_id}/block')
def receptionist_block_visit(visit_id: int, db: Session = Depends(get_db)):
    """Block all tests in a visit (receptionist action) - blocks without locking to a lab."""
    from app.models import TestItem, TestStatus
    tests = db.scalars(select(TestItem).where(TestItem.visit_id == visit_id)).all()
    for test in tests:
        if test.status not in {TestStatus.COMPLETED, TestStatus.IN_PROGRESS}:
            test.is_blocked = True
            test.caution_reason = 'Visit blocked by receptionist'
    db.commit()
    return {'message': 'Visit blocked', 'visit_id': visit_id}


@app.post('/api/visits/{visit_id}/unblock')
def receptionist_unblock_visit(visit_id: int, db: Session = Depends(get_db)):
    """Unblock all tests in a visit (receptionist action) - re-considers for scheduling."""
    from app.models import TestItem, TestStatus, QueueStatus
    tests = db.scalars(select(TestItem).where(TestItem.visit_id == visit_id)).all()
    for test in tests:
        if test.is_blocked:
            test.is_blocked = False
            test.caution_reason = None
            # Reset to WAITING so OR-Solver can re-assign to correct lab
            if test.queue_status != QueueStatus.CURRENT and test.status != TestStatus.IN_PROGRESS:
                test.queue_status = QueueStatus.WAITING
    db.commit()
    # Run OR optimization to re-assign
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    return {'message': 'Visit unblocked', 'visit_id': visit_id}


@app.get('/api/frontend/visits')
def get_frontend_visits(db: Session = Depends(get_db)):
    """Get all visits for the frontend Patient Records table."""
    from app.models import TestItem
    visits = db.scalars(select(Visit).options(selectinload(Visit.tests))).all()
    result = []
    for v in visits:
        test_names = [t.test_name for t in v.tests]
        # Determine status based on tests
        if any(t.status == TestStatus.IN_PROGRESS for t in v.tests):
            status = 'In Progress'
        elif all(t.status == TestStatus.COMPLETED for t in v.tests):
            status = 'Completed'
        elif any(t.is_blocked for t in v.tests):
            status = 'Blocked'
        elif any(t.queue_status == QueueStatus.PENDING for t in v.tests):
            status = 'Pending'
        else:
            status = 'Waiting'

        result.append({
            'id': v.public_id,
            'visit_id': v.id,
            'patient_name': v.patient_name,
            'patient_age': v.patient_age,
            'patient_gender': v.patient_gender,
            'phone': v.phone or 'N/A',
            'priority_type': v.priority_type,
            'status': status,
            'arrival_time': v.arrival_time.isoformat(),
            'tests': test_names
        })
    return result


@app.post('/api/lims/ingest')
async def ingest_patient_from_lims(request: Request, db: Session = Depends(get_db)):
    """Ingest patient data from LIMS webhook."""
    from app.models import TestItem, TestStatus, QueueStatus
    from app.catalog import test_catalog_map

    payload = await request.json()

    # 1. Create visit
    visit = Visit(
        public_id=_next_public_id(db, datetime.now()),
        phr_reference_id=payload.get('lims_patient_id') or f'LIMS-{datetime.now().strftime("%Y%m%d%H%M%S%f")}',
        patient_name=payload.get('patient_name', 'Unknown'),
        patient_age=payload.get('patient_age', 30),
        patient_gender=payload.get('gender', 'Any'),
        priority_type=payload.get('priority_type', 'Routine'),
        arrival_time=datetime.now().astimezone(),
        patient_snapshot={}
    )
    db.add(visit)
    db.flush()

    # 2. Add tests
    catalog = test_catalog_map()

    # Handle both payload formats securely
    tests_list = payload.get('requested_tests', payload.get('tests', []))

    for test_payload in tests_list:
        test_code = test_payload.get('test_id') or test_payload.get('test_code')
        test_name = test_payload.get('test_name')

        item = None
        if test_code:
            for v in catalog.values():
                if v['test_code'] == test_code:
                    item = v
                    break
        elif test_name and test_name in catalog:
            item = catalog[test_name]

        if item:
            status = TestStatus.SCHEDULED
            queue_status = QueueStatus.NOT_QUEUED

            # If Ultrasound, block it initially (requires full bladder)
            if item['test_code'] == 'T0063':
                queue_status = QueueStatus.PENDING

            db.add(TestItem(
                visit_id=visit.id,
                test_code=item['test_code'],
                test_name=item['test_name'],
                category=item['category'],
                duration_minutes=int(item['duration_minutes']),
                tags=list(item.get('tags', [])),
                status=status,
                queue_status=queue_status
            ))

    db.commit()

    # 3. Run OR optimization
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()

    return {
        'visit_id': visit.id,
        'public_id': visit.public_id,
        'message': 'Patient successfully routed by OR-Solver'
    }


# ===== Demo Data Seed Endpoints (For Development/Demo) =====
@app.post('/api/seed/lims-patients')
async def seed_lims_patients(db: Session = Depends(get_db)):
    """Seed patients from VISIT_TEMPLATES using PHR sync format."""
    from app.seed_data import VISIT_TEMPLATES
    
    created: list[str] = []
    catalog = test_catalog_map()
    
    for template in VISIT_TEMPLATES:
        # Skip if duplicate PHR reference already exists
        existing = db.scalar(
            select(Visit).where(Visit.phr_reference_id == template['phr_reference_id'])
        )
        if existing:
            continue
            
        # Build arrival time (today + template arrival_clock)
        now = datetime.now().astimezone()
        arrival_parts = template['arrival_clock'].split(':')
        arrival_time = now.replace(hour=int(arrival_parts[0]), minute=int(arrival_parts[1]), second=0, microsecond=0)
        
        snapshot = dict(template.get('patient_snapshot', {}))
        phone = snapshot.get('phone', '')
        
        visit = Visit(
            public_id=_next_public_id(db, arrival_time),
            phr_reference_id=template['phr_reference_id'],
            patient_name=template['patient_name'],
            patient_age=template['patient_age'],
            patient_gender=template['patient_gender'],
            priority_type=template['priority_type'],
            phone=phone or None,
            arrival_time=arrival_time,
            patient_snapshot=snapshot,
        )
        db.add(visit)
        db.flush()
        
        for test in template['tests']:
            db.add(TestItem(
                visit_id=visit.id,
                test_code=test['test_code'],
                test_name=test['test_name'],
                category=test['category'],
                duration_minutes=int(test.get('duration_minutes', 10)),
                tags=list(test.get('tags', [])),
                condition_category=test.get('condition_category'),
                status=TestStatus.SCHEDULED,
                queue_status=QueueStatus.WAITING,
            ))
        db.flush()
        created.append(visit.public_id)
    
    db.commit()
    
    # Run OR optimization for all new patients
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return {
        'created_count': len(created),
        'created': created,
        'message': f'{len(created)} LIMS patients seeded successfully'
    }


@app.post('/api/seed/specialists')
async def seed_mock_specialists(db: Session = Depends(get_db)):
    """Seed mock specialists from DEFAULT_SPECIALISTS."""
    from app.seed_data import DEFAULT_SPECIALISTS
    from datetime import time
    
    created: list[dict] = []
    
    for specialist_data in DEFAULT_SPECIALISTS:
        # Check if specialist with same name already exists
        existing = db.scalar(
            select(Specialist).where(Specialist.name == specialist_data['name'])
        )
        if existing:
            continue
        
        specialist = Specialist(
            name=specialist_data['name'],
            gender=specialist_data['gender'],
            shift_start=specialist_data['shift_start'],
            shift_end=specialist_data['shift_end'],
            is_active=True,
        )
        db.add(specialist)
        db.flush()
        created.append({
            'id': f's{specialist.id}',
            'name': specialist.name,
            'gender': specialist.gender,
        })
    
    db.commit()
    
    for item in created:
        emit_nowait('specialist.updated', item)
    
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    
    return {
        'created_count': len(created),
        'created': created,
        'message': f'{len(created)} mock specialists seeded successfully'
    }


@app.post('/api/seed/labs')
async def seed_mock_labs(db: Session = Depends(get_db)):
    """Seed mock labs from DEFAULT_LABS."""
    from app.seed_data import DEFAULT_LABS
    
    created: list[dict] = []
    
    # Get all specialists first
    specialists = db.scalars(select(Specialist)).all()
    specialist_dict = {i: spec for i, spec in enumerate(specialists, 1)}
    
    for lab_data in DEFAULT_LABS:
        # Check if lab with same name already exists
        existing = db.scalar(
            select(Lab).where(Lab.name == lab_data['name'])
        )
        if existing:
            continue
        
        # Get specialist based on index
        specialist_index = lab_data.get('specialist_index', 1)
        specialist_id = specialist_dict.get(specialist_index).id if specialist_index in specialist_dict else None
        
        lab = Lab(
            name=lab_data['name'],
            category=lab_data['category'],
            floor=lab_data['floor'],
            room_number=lab_data['room_number'],
            specialist_id=specialist_id,
            is_active=lab_data['is_active'],
            opening_time=lab_data['opening_time'],
            closing_time=lab_data['closing_time'],
            cleanup_duration_minutes=lab_data['cleanup_duration_minutes'],
            supported_test_codes=lab_data.get('supported_test_codes', []),
        )
        db.add(lab)
        db.flush()
        created.append({
            'id': f'l{lab.id}',
            'name': lab.name,
            'category': lab.category,
            'floor': lab.floor,
        })
    
    db.commit()
    
    # Trigger OR optimization for new labs
    or_scheduler = ORScheduler(db)
    or_scheduler.run_optimization()
    db.commit()
    
    for item in created:
        emit_nowait('lab.updated', item)
    
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    
    return {
        'created_count': len(created),
        'created': created,
        'message': f'{len(created)} mock labs seeded successfully'
    }


application = mount(app)
