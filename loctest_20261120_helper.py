from datetime import date
from typing import Optional


def calculate_age(birth_date: date, today: Optional[date] = None) -> int:
    """Return full years elapsed since birth_date."""
    reference_date = today or date.today()
    if not isinstance(birth_date, date):
        raise TypeError("birth_date must be a date")
    if birth_date > reference_date:
        raise ValueError("birth_date cannot be in the future")
    birthday_passed = (reference_date.month, reference_date.day) >= (birth_date.month, birth_date.day)
    return reference_date.year - birth_date.year - int(not birthday_passed)
