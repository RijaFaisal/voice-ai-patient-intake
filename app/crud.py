from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas


def get_patient(db: Session, patient_id: str, include_deleted: bool = False) -> Optional[models.Patient]:
    query = db.query(models.Patient).filter(models.Patient.patient_id == patient_id)
    if not include_deleted:
        query = query.filter(models.Patient.deleted_at.is_(None))
    return query.first()


def get_patient_by_phone(db: Session, phone_number: str) -> Optional[models.Patient]:
    return (
        db.query(models.Patient)
        .filter(models.Patient.phone_number == phone_number, models.Patient.deleted_at.is_(None))
        .first()
    )


def list_patients(
    db: Session,
    last_name: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    phone_number: Optional[str] = None,
) -> List[models.Patient]:
    query = db.query(models.Patient).filter(models.Patient.deleted_at.is_(None))
    if last_name:
        query = query.filter(func.lower(models.Patient.last_name) == last_name.strip().lower())
    if date_of_birth:
        query = query.filter(models.Patient.date_of_birth == date_of_birth)
    if phone_number:
        query = query.filter(models.Patient.phone_number == phone_number)
    return query.order_by(models.Patient.last_name, models.Patient.first_name).all()


def create_patient(db: Session, patient_in: schemas.PatientCreate) -> models.Patient:
    now = datetime.utcnow()
    db_patient = models.Patient(**patient_in.model_dump(), created_at=now, updated_at=now)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def update_patient(db: Session, db_patient: models.Patient, patient_in: schemas.PatientUpdate) -> models.Patient:
    update_data = patient_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_patient, field, value)
    db_patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_patient)
    return db_patient


def soft_delete_patient(db: Session, db_patient: models.Patient) -> models.Patient:
    now = datetime.utcnow()
    db_patient.deleted_at = now
    db_patient.updated_at = now
    db.commit()
    db.refresh(db_patient)
    return db_patient


def get_appointment(db: Session, appointment_id: str) -> Optional[models.Appointment]:
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.appointment_id == appointment_id, models.Appointment.deleted_at.is_(None))
        .first()
    )


def list_appointments(db: Session, patient_id: Optional[str] = None) -> List[models.Appointment]:
    query = db.query(models.Appointment).filter(models.Appointment.deleted_at.is_(None))
    if patient_id:
        query = query.filter(models.Appointment.patient_id == patient_id)
    return query.order_by(models.Appointment.appointment_date).all()


def create_appointment(db: Session, appointment_in: schemas.AppointmentCreate) -> models.Appointment:
    db_appointment = models.Appointment(**appointment_in.model_dump(), created_at=datetime.utcnow())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment
