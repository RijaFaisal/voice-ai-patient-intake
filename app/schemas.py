from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from . import validators as v
from .models import Sex


class PatientBase(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    date_of_birth: date
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
    preferred_language: str = Field(default="English", max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = None

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

    @field_validator("date_of_birth")
    @classmethod
    def _date_of_birth(cls, val: date) -> date:
        return v.validate_dob(val)

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
    date_of_birth: Optional[date] = None
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

    @field_validator("date_of_birth")
    @classmethod
    def _date_of_birth(cls, val):
        return val if val is None else v.validate_dob(val)

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


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class Envelope(BaseModel):
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
