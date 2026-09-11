import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String

from .database import Base


class Sex(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE_TO_ANSWER = "Decline to Answer"


class Patient(Base):
    """
    Patient demographic record.

    Field requirement levels follow common US ambulatory patient-intake
    practice (e.g. CMS-1500 / HL7 demographic segments): identity, DOB,
    sex, one contact phone, and a mailing address are required to register
    and bill a patient; email, insurance, preferred language, and emergency
    contact are collected when available but are not blocking.
    """

    __tablename__ = "patients"

    patient_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Required
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    sex = Column(SAEnum(Sex, native_enum=False, length=20), nullable=False)
    phone_number = Column(String(10), nullable=False)
    address_line_1 = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)

    # Optional
    email = Column(String(255), nullable=True)
    address_line_2 = Column(String(255), nullable=True)
    insurance_provider = Column(String(100), nullable=True)
    insurance_member_id = Column(String(50), nullable=True)
    preferred_language = Column(String(50), nullable=False, default="English")
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(10), nullable=True)

    # System-managed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class Appointment(Base):
    """Scheduled appointment for a patient."""

    __tablename__ = "appointments"

    appointment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)

    # System-managed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
