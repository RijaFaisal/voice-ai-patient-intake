import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas, validators
from ..database import get_db

router = APIRouter(prefix="/patients", tags=["patients"])
logger = logging.getLogger("patient_api")


def _serialize(record) -> dict:
    return schemas.PatientOut.model_validate(record).model_dump(mode="json")


@router.get("", status_code=status.HTTP_200_OK)
def list_patients(
    last_name: Optional[str] = Query(None, description="Filter by exact last name (case-insensitive)"),
    date_of_birth: Optional[date] = Query(None, description="Filter by date of birth, YYYY-MM-DD"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number, any common US format"),
    db: Session = Depends(get_db),
):
    normalized_phone = None
    if phone_number:
        try:
            normalized_phone = validators.validate_phone(phone_number, "phone_number")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    records = crud.list_patients(
        db, last_name=last_name, date_of_birth=date_of_birth, phone_number=normalized_phone
    )
    return {"data": [_serialize(r) for r in records], "error": None}


def _lookup_by_phone(phone_number: str, db: Session) -> dict:
    try:
        normalized_phone = validators.validate_phone(phone_number, "phone_number")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    record = crud.get_patient_by_phone(db, normalized_phone)
    return {"data": _serialize(record) if record else None, "error": None}


@router.get("/lookup", status_code=status.HTTP_200_OK)
def lookup_patient(
    phone_number: str = Query(..., description="Phone number to look up, any common US format"),
    db: Session = Depends(get_db),
):
    return _lookup_by_phone(phone_number, db)


@router.get("/lookup/{phone_number}", status_code=status.HTTP_200_OK)
def lookup_patient_by_path(phone_number: str, db: Session = Depends(get_db)):
    return _lookup_by_phone(phone_number, db)


@router.get("/{patient_id}", status_code=status.HTTP_200_OK)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    record = crud.get_patient(db, patient_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")
    return {"data": _serialize(record), "error": None}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_patient(patient_in: schemas.PatientCreate, db: Session = Depends(get_db)):
    payload = patient_in.model_dump(mode="json")
    logger.info("Collected patient registration payload: %s", payload)

    record = crud.create_patient(db, patient_in)
    return {"data": _serialize(record), "error": None}


@router.put("/{patient_id}", status_code=status.HTTP_200_OK)
def update_patient(patient_id: str, patient_in: schemas.PatientUpdate, db: Session = Depends(get_db)):
    record = crud.get_patient(db, patient_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")

    payload = patient_in.model_dump(mode="json", exclude_unset=True)
    logger.info("Collected patient update payload for %s: %s", patient_id, payload)

    updated = crud.update_patient(db, record, patient_in)
    return {"data": _serialize(updated), "error": None}


@router.delete("/{patient_id}", status_code=status.HTTP_200_OK)
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    record = crud.get_patient(db, patient_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")

    deleted = crud.soft_delete_patient(db, record)
    logger.info("Soft-deleted patient %s at %s", patient_id, deleted.deleted_at.isoformat())
    return {"data": _serialize(deleted), "error": None}
