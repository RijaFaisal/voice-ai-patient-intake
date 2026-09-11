from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from . import validators as v
from .models import Sex


class PatientBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    date_of_birth: date = Field(
        ...,
        description=(
            "Date of birth in MM/DD/YYYY format (e.g. 04/12/1988). "
            "YYYY-MM-DD is also accepted for backward compatibility."
        ),
        examples=["04/12/1988"],
    )
    sex: Sex
    phone_number: str
    address_line_1: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str
    zip_code: str

    email: Optional[EmailStr] = None
    address_line_2: Optional[str] = Field(None, max_length=255)
    insurance_provider: Optional[str] = Field(None, max_length=100)
    insurance_member_id: Optional[str] = Field(None, max_length=50)
    preferred_language: Optional[str] = Field(default="English", max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = None

    @field_validator(
        "email",
        "address_line_2",
        "insurance_provider",
        "insurance_member_id",
        "preferred_language",
        "emergency_contact_name",
        "emergency_contact_phone",
        mode="before",
    )
    @classmethod
    def _empty_optional_to_none(cls, val):
        return v.empty_str_to_none(val)

    @field_validator("first_name")
    @classmethod
    def _first_name(cls, val: str) -> str:
        return v.validate_name(val, "First name")

    @field_validator("last_name")
    @classmethod
    def _last_name(cls, val: str) -> str:
        return v.validate_name(val, "Last name")

    @field_validator("emergency_contact_name")
    @classmethod
    def _emergency_contact_name(cls, val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        return v.validate_name(val, "Emergency contact name")

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def _date_of_birth(cls, val):
        return v.parse_date_of_birth(val)

    @field_validator("phone_number")
    @classmethod
    def _phone_number(cls, val: str) -> str:
        return v.validate_phone(val, "Phone number")

    @field_validator("emergency_contact_phone")
    @classmethod
    def _emergency_contact_phone(cls, val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        return v.validate_phone(val, "Emergency contact phone")

    @field_validator("state")
    @classmethod
    def _state(cls, val: str) -> str:
        return v.validate_state(val)

    @field_validator("zip_code")
    @classmethod
    def _zip_code(cls, val: str) -> str:
        return v.validate_zip(val)

    @field_validator("preferred_language")
    @classmethod
    def _preferred_language(cls, val: Optional[str]) -> str:
        val = (val or "English").strip()
        return val or "English"

    @field_validator("address_line_1", "city")
    @classmethod
    def _required_text(cls, val: str) -> str:
        val = (val or "").strip()
        if not val:
            raise ValueError("This field is required and cannot be blank.")
        return val

    @field_validator("address_line_2", "insurance_provider", "insurance_member_id")
    @classmethod
    def _optional_text(cls, val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        val = val.strip()
        return val or None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    """Partial-update schema for PUT /patients/{id}: every field optional."""

    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = Field(
        None,
        description=(
            "Date of birth in MM/DD/YYYY format (e.g. 04/12/1988). "
            "YYYY-MM-DD is also accepted for backward compatibility."
        ),
        examples=["04/12/1988"],
    )
    sex: Optional[Sex] = None
    phone_number: Optional[str] = None
    address_line_1: Optional[str] = Field(None, min_length=1, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = None
    zip_code: Optional[str] = None

    email: Optional[EmailStr] = None
    address_line_2: Optional[str] = Field(None, max_length=255)
    insurance_provider: Optional[str] = Field(None, max_length=100)
    insurance_member_id: Optional[str] = Field(None, max_length=50)
    preferred_language: Optional[str] = Field(None, max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = None

    @field_validator(
        "email",
        "address_line_2",
        "insurance_provider",
        "insurance_member_id",
        "preferred_language",
        "emergency_contact_name",
        "emergency_contact_phone",
        mode="before",
    )
    @classmethod
    def _empty_optional_to_none(cls, val):
        return v.empty_str_to_none(val)

    @field_validator("first_name")
    @classmethod
    def _first_name(cls, val):
        return val if val is None else v.validate_name(val, "First name")

    @field_validator("last_name")
    @classmethod
    def _last_name(cls, val):
        return val if val is None else v.validate_name(val, "Last name")

    @field_validator("emergency_contact_name")
    @classmethod
    def _emergency_contact_name(cls, val):
        if not val:
            return None
        return v.validate_name(val, "Emergency contact name")

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def _date_of_birth(cls, val):
        return None if val is None else v.parse_date_of_birth(val)

    @field_validator("phone_number")
    @classmethod
    def _phone_number(cls, val):
        return val if val is None else v.validate_phone(val, "Phone number")

    @field_validator("emergency_contact_phone")
    @classmethod
    def _emergency_contact_phone(cls, val):
        if not val:
            return None
        return v.validate_phone(val, "Emergency contact phone")

    @field_validator("state")
    @classmethod
    def _state(cls, val):
        return val if val is None else v.validate_state(val)

    @field_validator("zip_code")
    @classmethod
    def _zip_code(cls, val):
        return val if val is None else v.validate_zip(val)

    @field_validator("preferred_language")
    @classmethod
    def _preferred_language(cls, val):
        if val is None:
            return None
        val = val.strip()
        return val or None

    @field_validator("address_line_1", "city")
    @classmethod
    def _required_text(cls, val):
        if val is None:
            return None
        val = val.strip()
        if not val:
            raise ValueError("This field cannot be blank.")
        return val

    @field_validator("address_line_2", "insurance_provider", "insurance_member_id")
    @classmethod
    def _optional_text(cls, val):
        if val is None:
            return None
        val = val.strip()
        return val or None


class PatientOut(PatientBase):
    patient_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentCreate(BaseModel):
    patient_id: str
    appointment_date: datetime = Field(
        ...,
        description="Appointment date/time, ISO 8601 (e.g. 2026-10-01T14:30:00). Cannot be in the past.",
        examples=["2026-10-01T14:30:00"],
    )
    reason: Optional[str] = Field(None, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def _empty_reason_to_none(cls, val):
        return v.empty_str_to_none(val)

    @field_validator("reason")
    @classmethod
    def _reason(cls, val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        val = val.strip()
        return val or None

    @field_validator("appointment_date")
    @classmethod
    def _appointment_date(cls, val: datetime) -> datetime:
        if val < datetime.utcnow():
            raise ValueError("Appointment date cannot be in the past.")
        return val


class AppointmentOut(BaseModel):
    appointment_id: str
    patient_id: str
    appointment_date: datetime
    reason: Optional[str] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class Envelope(BaseModel):
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
