"""
Shared server-side validation rules for patient intake fields.

Kept separate from app/schemas.py so the same rules can be reused by both
the Pydantic request/response models and the plain query-parameter
filters used in GET /patients.
"""
import re
from datetime import date, datetime

NAME_RE = re.compile(r"^[A-Za-zÀ-ſ](?:[A-Za-zÀ-ſ'\-. ]*[A-Za-zÀ-ſ.])?$")

# Accepts: 1234567890 | 123-456-7890 | 123.456.7890 | (123) 456-7890
# | +1 123 456 7890 | 1 123-456-7890 -- always normalized to 10 digits.
PHONE_RE = re.compile(r"^\+?1?[\s.\-]?\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})$")

# Looser than PHONE_RE: matches a run of digits (with spaces/dots/dashes/
# parens as separators, no letters) anywhere inside free-form text, for
# scanning a call transcript rather than validating a standalone field.
# Deliberately permissive about grouping since transcription can render a
# spoken number unevenly (e.g. "415. 55. 5. 777. 8" for 415-555-7778).
TRANSCRIPT_PHONE_CHUNK_RE = re.compile(r"\d[\d\s().\-]*\d")

ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")

# Primary format per spec: MM/DD/YYYY (e.g. 04/12/1988).
# ISO YYYY-MM-DD is also accepted for backward compatibility.
MM_DD_YYYY_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "AS", "GU", "MP", "PR", "VI",
}

MIN_BIRTH_YEAR_SPAN = 150  # generous upper bound on plausible patient age


def empty_str_to_none(value):
    """Treat an empty or whitespace-only string as 'not provided'."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


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


def extract_phone_candidates(text: str) -> list:
    """
    Scan free-form text (e.g. a call transcript) for substrings that look
    like a US phone number and return each as a normalized 10-digit string,
    in the order they appear. Used as a fallback when no reliable caller ID
    is available (e.g. a Vapi web call), so it can't rely on the strict,
    anchored format validate_phone() expects.
    """
    candidates = []
    for match in TRANSCRIPT_PHONE_CHUNK_RE.finditer(text or ""):
        digits = re.sub(r"\D", "", match.group())
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            candidates.append(digits)
    return candidates


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


def parse_date_of_birth(value) -> date:
    """
    Accepts MM/DD/YYYY (primary, per spec) or ISO YYYY-MM-DD (backward
    compatibility), or an already-parsed date/datetime. Rejects anything
    else. Applies validate_dob() to the result before returning.
    """
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        parsed = None

        if MM_DD_YYYY_RE.match(text):
            try:
                parsed = datetime.strptime(text, "%m/%d/%Y").date()
            except ValueError:
                parsed = None

        if parsed is None and ISO_DATE_RE.match(text):
            try:
                parsed = datetime.strptime(text, "%Y-%m-%d").date()
            except ValueError:
                parsed = None

        if parsed is None:
            raise ValueError(
                "Date of birth must be in MM/DD/YYYY format (e.g. 04/12/1988); "
                "YYYY-MM-DD (e.g. 1988-04-12) is also accepted."
            )
    else:
        raise ValueError("Date of birth must be a date string in MM/DD/YYYY format.")

    return validate_dob(parsed)
