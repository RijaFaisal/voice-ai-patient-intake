"""
Shared server-side validation rules for patient intake fields.

Kept separate from app/schemas.py so the same rules can be reused by both
the Pydantic request/response models and the plain query-parameter
filters used in GET /patients.
"""
import re
from datetime import date

NAME_RE = re.compile(r"^[A-Za-zÀ-ſ](?:[A-Za-zÀ-ſ'\-. ]*[A-Za-zÀ-ſ.])?$")

# Accepts: 1234567890 | 123-456-7890 | 123.456.7890 | (123) 456-7890
# | +1 123 456 7890 | 1 123-456-7890 -- always normalized to 10 digits.
PHONE_RE = re.compile(r"^\+?1?[\s.\-]?\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})$")

ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI",
}

MIN_BIRTH_YEAR_SPAN = 150  # generous upper bound on plausible patient age


def validate_name(value: str, field_name: str = "Name") -> str:
    value = (value or "").strip()
    if not (1 <= len(value) <= 50):
        raise ValueError(f"{field_name} must be between 1 and 50 characters.")
    if not NAME_RE.match(value):
        raise ValueError(
            f"{field_name} may only contain letters, spaces, hyphens, apostrophes, and periods."
        )
    return value


def validate_phone(value: str, field_name: str = "Phone number") -> str:
    match = PHONE_RE.match((value or "").strip())
    if not match:
        raise ValueError(
            f"{field_name} must be a valid 10-digit US phone number "
            f"(e.g. 415-555-0132 or (415) 555-0132)."
        )
    return "".join(match.groups())


def validate_state(value: str) -> str:
    v = (value or "").strip().upper()
    if v not in US_STATES:
        raise ValueError("State must be a valid 2-letter USPS state or territory abbreviation.")
    return v


def validate_zip(value: str) -> str:
    v = (value or "").strip()
    if not ZIP_RE.match(v):
        raise ValueError("ZIP code must be in 5-digit or ZIP+4 format (e.g. 94110 or 94110-1234).")
    return v


def validate_dob(value: date) -> date:
    today = date.today()
    if value > today:
        raise ValueError("Date of birth cannot be in the future.")
    try:
        min_date = today.replace(year=today.year - MIN_BIRTH_YEAR_SPAN)
    except ValueError:
        # Feb 29 with no matching leap year that far back.
        min_date = today.replace(month=2, day=28, year=today.year - MIN_BIRTH_YEAR_SPAN)
    if value < min_date:
        raise ValueError("Date of birth is not plausible.")
    return value
