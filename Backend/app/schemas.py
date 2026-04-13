from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SpecialistPayload(BaseModel):
    name: str
    gender: str
    shift_start: str
    shift_end: str
    is_active: bool = True


class LabPayload(BaseModel):
    name: str
    category: str
    floor: str
    room_number: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    cleanup_duration_minutes: int = 0
    is_active: bool = True
    specialist_id: int | None = None


class VisitPayload(BaseModel):
    phr_reference_id: str
    patient_name: str
    patient_age: int
    patient_gender: str
    priority_type: str
    phone: str | None = None
    arrival_time: datetime
    patient_snapshot: dict[str, Any] = Field(default_factory=dict)
    tests: list[dict[str, Any]]


class FrontendPatientPayload(BaseModel):
    patient_name: str
    patient_age: int
    patient_gender: str
    priority_type: str = 'NORMAL'
    phone: str = ''
    test_names: list[str] = Field(default_factory=list)


class AcceptPendingPayload(BaseModel):
    visit_test_id: int | None = None


class VisitListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_more: bool


class DeltaResponse(BaseModel):
    since: datetime | None = None
    now: datetime
    visits: list[dict[str, Any]]
    labs: list[dict[str, Any]]
    specialists: list[dict[str, Any]]
    metrics: dict[str, Any]
