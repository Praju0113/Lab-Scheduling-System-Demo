from __future__ import annotations

from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import AssignmentHistory, CompletedTestSnapshot, ExplicitDependencies, Lab, QueueCursor, QueueEntry, Specialist, TestItem, Visit
from app.seed_data import DEFAULT_LABS, DEFAULT_SPECIALISTS, build_seed_visits
from app.services.patient_ids import build_patient_id, patient_id_date


def reset_database(session: Session) -> None:
    session.execute(delete(CompletedTestSnapshot))
    session.execute(delete(AssignmentHistory))
    session.execute(delete(QueueEntry))
    session.execute(delete(QueueCursor))
    session.execute(delete(TestItem))
    session.execute(delete(ExplicitDependencies))
    session.execute(delete(Visit))
    session.execute(delete(Lab))
    session.execute(delete(Specialist))
    session.commit()


# Medical test dependencies (recommended sequence, not strict blocking)
TEST_DEPENDENCIES = [
    # TMT (Treadmill Test) - Recommended after ECG for baseline vitals
    {'test_code': 'TMT', 'depends_on_test_code': 'ECG', 'dependency_type': 'recommended_after', 'is_strict': False},
    # Dual-phase tests - Fasting sample should be done before post-prandial
    {'test_code': 'Glucose-PostPrandial', 'depends_on_test_code': 'Glucose-Fasting', 'dependency_type': 'must_complete_before', 'is_strict': True},
    {'test_code': 'Insulin-PostPrandial', 'depends_on_test_code': 'Insulin-Fasting', 'dependency_type': 'must_complete_before', 'is_strict': True},
    # Urine should be done before Ultrasound if bladder needs to be full
    {'test_code': 'Ultrasound-Abdomen', 'depends_on_test_code': 'Urine-Examination', 'dependency_type': 'recommended_after', 'is_strict': False},
]


def seed_dependencies(session: Session) -> None:
    """Seed explicit test dependencies for OR solver."""
    existing = session.scalar(select(func.count()).select_from(ExplicitDependencies))
    if existing > 0:
        return
    
    for dep in TEST_DEPENDENCIES:
        session.add(ExplicitDependencies(**dep))
    session.commit()


def seed_database(session: Session, base_date: date | None = None) -> None:
    if session.scalar(select(func.count()).select_from(Specialist)):
        return
    specialists = []
    for row in DEFAULT_SPECIALISTS:
        specialist = Specialist(**row)
        session.add(specialist)
        specialists.append(specialist)
    session.flush()
    for row in DEFAULT_LABS:
        specialist = specialists[row['specialist_index'] - 1]
        session.add(Lab(
            name=row['name'],
            category=row['category'],
            floor=row['floor'],
            room_number=row['room_number'],
            specialist_id=specialist.id,
            is_active=row['is_active'],
            opening_time=row['opening_time'],
            closing_time=row['closing_time'],
            cleanup_duration_minutes=row['cleanup_duration_minutes'],
            supported_test_codes=row['supported_test_codes'],
        ))
    session.flush()
    daily_sequences: dict[date, int] = {}
    visits_to_seed = sorted(build_seed_visits(base_date=base_date), key=lambda row: row['arrival_time'])
    for visit_row in visits_to_seed:
        visit_date = patient_id_date(visit_row['arrival_time'])
        sequence = daily_sequences.get(visit_date, 0)
        daily_sequences[visit_date] = sequence + 1
        visit = Visit(
            public_id=build_patient_id(visit_date, sequence),
            phr_reference_id=visit_row['phr_reference_id'],
            patient_name=visit_row['patient_name'],
            patient_age=visit_row['patient_age'],
            patient_gender=visit_row['patient_gender'],
            priority_type=visit_row['priority_type'],
            arrival_time=visit_row['arrival_time'],
            patient_snapshot=visit_row.get('patient_snapshot', {}),
        )
        session.add(visit)
        session.flush()
        for test_row in visit_row['tests']:
            session.add(TestItem(
                visit_id=visit.id,
                test_code=test_row['test_code'],
                test_name=test_row['test_name'],
                category=test_row['category'],
                duration_minutes=test_row['duration_minutes'],
                tags=test_row.get('tags', []),
                condition_category=test_row.get('condition_category'),
            ))
    session.commit()
    seed_dependencies(session)
