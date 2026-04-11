from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
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


@app.on_event('startup')
def startup() -> None:
    _ensure_schema()
    with SessionLocal() as session:
        if settings.reset_db_on_startup:
            reset_database(session)
        if settings.seed_on_startup:
            seed_database(session)
            scheduler = SchedulingService(session)
            scheduler.schedule_all()
            session.commit()


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
    scheduler = SchedulingService(db)
    scheduler.rebuild_for_visit(visit.id, reason=reason)
    db.flush()
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
    scheduler = SchedulingService(db)
    scheduler.rebuild_for_visit(visit.id, reason='frontend patient created')
    db.commit()
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
    scheduler = SchedulingService(db)
    scheduler.reschedule_for_specialist(specialist.id, reason='specialist updated')
    scheduler.refill_all_queues()
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
    SchedulingService(db).refill_lab_queue(lab.id)
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
    scheduler = SchedulingService(db)
    scheduler.reschedule_for_lab(lab.id, reason='lab updated')
    scheduler.refill_all_queues()
    db.commit()
    response = frontend_lab(db, lab)
    emit_nowait('lab.updated', response)
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return response


@app.delete('/api/labs/{lab_id}')
async def delete_lab(lab_id: int, db: Session = Depends(get_db)):
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail='Lab not found')
    affected_tests = db.scalars(select(TestItem).where(TestItem.assigned_lab_id == lab_id, TestItem.status != 'COMPLETED')).all()
    for test in affected_tests:
        test.assigned_lab_id = None
        test.status = 'UNSCHEDULABLE'
        test.queue_status = 'NOT_QUEUED'
        test.caution_reason = 'Assigned lab was deleted.'
    db.delete(lab)
    SchedulingService(db).refill_all_queues()
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
    emit_nowait('queue.updated', {'labId': f'l{lab_id}', 'snapshot': snapshot})
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return snapshot


@app.post('/api/phr-sync/patients')
async def phr_sync_patients(payload: list[VisitPayload], db: Session = Depends(get_db)):
    created: list[str] = []
    scheduler = SchedulingService(db)
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
            db.add(TestItem(visit_id=visit.id, test_code=test_payload['test_code'], test_name=test_payload['test_name'], category=test_payload['category'], duration_minutes=int(test_payload.get('duration_minutes', 10)), tags=list(test_payload.get('tags', [])), condition_category=test_payload.get('condition_category')))
        db.flush()
        scheduler.rebuild_for_visit(visit.id, reason='phr sync')
        created.append(visit.public_id)
    db.commit()
    emit_nowait('visit.updated', {'created': created})
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return {'created': created}


@app.post('/api/scheduling/run')
async def run_scheduling(db: Session = Depends(get_db)):
    scheduler = SchedulingService(db)
    scheduler.schedule_all()
    db.commit()
    emit_nowait('dashboard.metrics.updated', admin_dashboard_payload(db))
    return {'message': 'Scheduling refreshed'}


application = mount(app)
