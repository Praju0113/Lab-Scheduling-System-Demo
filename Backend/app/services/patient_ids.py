from __future__ import annotations

from datetime import date, datetime

MONTH_CODES = {
    1: 'JA',
    2: 'FE',
    3: 'MA',
    4: 'AP',
    5: 'MY',
    6: 'JU',
    7: 'JL',
    8: 'AU',
    9: 'SE',
    10: 'OT',
    11: 'NO',
    12: 'DE',
}


def build_patient_id(for_date: date, sequence: int) -> str:
    month_code = MONTH_CODES[for_date.month]
    return f"{month_code}-{for_date.day:02d}-{sequence:03d}"


def extract_sequence(public_id: str, for_date: date) -> int | None:
    prefix = f"{MONTH_CODES[for_date.month]}-{for_date.day:02d}-"
    if not public_id.startswith(prefix):
        return None
    try:
        return int(public_id.split('-')[-1])
    except ValueError:
        return None


def patient_id_date(value: datetime) -> date:
    return value.astimezone().date() if value.tzinfo else value.date()
