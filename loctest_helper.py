from datetime import date
from typing import Optional


def calculate_age(birth_date: date, on_date: Optional[date] = None) -> int:
    """Return the number of full years elapsed since birth_date."""
    reference_date = on_date or date.today()
    if birth_date > reference_date:
        raise ValueError("birth_date cannot be in the future")
    had_birthday = (reference_date.month, reference_date.day) >= (birth_date.month, birth_date.day)
    return reference_date.year - birth_date.year - int(not had_birthday)
