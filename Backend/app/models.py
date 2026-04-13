from __future__ import annotations

from datetime import datetime, time
from enum import Enum

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TestStatus(str, Enum):
    SCHEDULED = 'SCHEDULED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    UNSCHEDULABLE = 'UNSCHEDULABLE'


class QueueStatus(str, Enum):
    NOT_QUEUED = 'NOT_QUEUED'
    WAITING = 'WAITING'
    CURRENT = 'CURRENT'
    PENDING = 'PENDING'
    DONE = 'DONE'


class QueueEntryType(str, Enum):
    CURRENT = 'CURRENT'
    NEXT = 'NEXT'
    PENDING = 'PENDING'


class Specialist(Base):
    __tablename__ = 'specialists'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    shift_start: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    labs = relationship('Lab', back_populates='specialist')


class Lab(Base):
    __tablename__ = 'labs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    floor: Mapped[str] = mapped_column(String(80), nullable=False)
    room_number: Mapped[str | None] = mapped_column(String(80))
    opening_time: Mapped[time] = mapped_column(Time, nullable=False)
    closing_time: Mapped[time] = mapped_column(Time, nullable=False)
    cleanup_duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    supported_test_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    specialist_id: Mapped[int | None] = mapped_column(ForeignKey('specialists.id', ondelete='SET NULL'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    specialist = relationship('Specialist', back_populates='labs')
    queue_entries = relationship('QueueEntry', back_populates='lab', cascade='all, delete-orphan')


class Visit(Base):
    __tablename__ = 'visits'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    phr_reference_id: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    patient_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    patient_age: Mapped[int] = mapped_column(Integer, nullable=False)
    patient_gender: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    patient_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tests = relationship('TestItem', back_populates='visit', cascade='all, delete-orphan')


class TestItem(Base):
    __tablename__ = 'test_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey('visits.id', ondelete='CASCADE'), nullable=False, index=True)
    test_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    condition_category: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[TestStatus] = mapped_column(SqlEnum(TestStatus), default=TestStatus.SCHEDULED, nullable=False, index=True)
    queue_status: Mapped[QueueStatus] = mapped_column(SqlEnum(QueueStatus), default=QueueStatus.NOT_QUEUED, nullable=False, index=True)
    assigned_lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id', ondelete='SET NULL'), index=True)
    sequence_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    caution_reason: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    visit = relationship('Visit', back_populates='tests')
    assigned_lab = relationship('Lab')
    queue_entries = relationship('QueueEntry', back_populates='test_item', cascade='all, delete-orphan')
    assignment_history = relationship('AssignmentHistory', back_populates='test_item', cascade='all, delete-orphan')
    completed_snapshots = relationship('CompletedTestSnapshot', back_populates='test_item', cascade='all, delete-orphan')


class QueueEntry(Base):
    __tablename__ = 'queue_entries'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey('labs.id', ondelete='CASCADE'), nullable=False, index=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey('visits.id', ondelete='CASCADE'), nullable=False, index=True)
    test_item_id: Mapped[int] = mapped_column(ForeignKey('test_items.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    queue_type: Mapped[QueueEntryType] = mapped_column(SqlEnum(QueueEntryType), nullable=False, index=True)
    position: Mapped[int | None] = mapped_column(Integer)
    pending_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    lab = relationship('Lab', back_populates='queue_entries')
    visit = relationship('Visit')
    test_item = relationship('TestItem', back_populates='queue_entries')


class QueueCursor(Base):
    __tablename__ = 'queue_cursors'

    lab_id: Mapped[int] = mapped_column(ForeignKey('labs.id', ondelete='CASCADE'), primary_key=True)
    consecutive_pending_accepts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AssignmentHistory(Base):
    __tablename__ = 'assignment_history'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_item_id: Mapped[int] = mapped_column(ForeignKey('test_items.id', ondelete='CASCADE'), nullable=False, index=True)
    from_lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id', ondelete='SET NULL'))
    to_lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id', ondelete='SET NULL'))
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    test_item = relationship('TestItem', back_populates='assignment_history')


class CompletedTestSnapshot(Base):
    __tablename__ = 'completed_test_snapshots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    patient_public_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    patient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    visit_id: Mapped[int] = mapped_column(ForeignKey('visits.id', ondelete='CASCADE'), nullable=False, index=True)
    test_item_id: Mapped[int] = mapped_column(ForeignKey('test_items.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id', ondelete='SET NULL'), index=True)
    lab_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    test_item = relationship('TestItem', back_populates='completed_snapshots')
