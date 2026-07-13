"""
Date parsing utilities.

Wraps dateparser for robust handling of the many date formats
found in resumes: "Jan 2020", "06/2019", "2021-Present", etc.
"""
import re
from datetime import date, datetime
from typing import Optional

import dateparser

# Tokens that indicate the position is current/ongoing
_PRESENT_TOKENS = frozenset(
    {
        "present",
        "current",
        "till date",
        "till now",
        "ongoing",
        "now",
        "today",
        "currently",
        "-",
        "–",
        "—",
    }
)

_DATEPARSER_SETTINGS = {
    "PREFER_DAY_OF_MONTH": "first",
    "RETURN_AS_TIMEZONE_AWARE": False,
    "PREFER_LOCALE_DATE_ORDER": True,
}


def parse_date(raw: str) -> Optional[date]:
    """
    Parse a raw date string extracted from a resume into a Python date.

    Handles formats:
    - "Jan 2020", "January 2020"
    - "2020-01", "01/2020", "06/2019"
    - "March 2023", "march 2023"
    - "2021", "2021-2023"
    - "Present", "Current" → None (caller treats as today)

    Returns:
        date object or None if the string is unparseable.
    """
    if not raw:
        return None

    cleaned = raw.strip().lower()

    if cleaned in _PRESENT_TOKENS:
        return None  # Caller interprets None as "today"

    # Try dateparser first
    parsed = dateparser.parse(raw, settings=_DATEPARSER_SETTINGS)  # type: ignore[arg-type]
    if parsed:
        return parsed.date()

    # Fallback: try yyyy-mm and yyyy patterns
    m = re.match(r"^(\d{4})-(\d{2})$", raw.strip())
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)

    m = re.match(r"^(\d{4})$", raw.strip())
    if m:
        return date(int(m.group(1)), 1, 1)

    return None


def is_present(raw: str) -> bool:
    """Return True if the raw date string indicates a current position."""
    return raw.strip().lower() in _PRESENT_TOKENS


def calc_duration_months(
    start: Optional[date],
    end: Optional[date],
    is_current: bool = False,
) -> int:
    """
    Calculate the number of months between two dates.

    If end is None and is_current is True, uses today as end date.

    Returns:
        Integer number of months (minimum 0).
    """
    if start is None:
        return 0

    effective_end = end or (date.today() if is_current else None)
    if effective_end is None:
        return 0

    months = (effective_end.year - start.year) * 12 + (
        effective_end.month - start.month
    )
    return max(0, months)


def months_to_years_months(months: int) -> str:
    """Format an integer months value as a human-readable string."""
    years, rem = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if rem:
        parts.append(f"{rem} month{'s' if rem > 1 else ''}")
    return " ".join(parts) if parts else "0 months"
