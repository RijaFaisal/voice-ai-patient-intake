import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/appointments", tags=["appointments"])
logger = logging.getLogger("patient_api")


def _serialize(record) -> dict:
    return schemas.AppointmentOut.model_validate(record).model_dump(mode="json")


@router.get("", status_code=status.HTTP_200_OK)
def list_appointments(
    patient_id: Optional[str] = Query(None, description="Filter by patient_id"),
    db: Session = Depends(get_db),
):
    records = crud.list_appointments(db, patient_id=patient_id)
    return {"data": [_serialize(r) for r in records], "error": None}


@router.get("/{appointment_id}", status_code=status.HTTP_200_OK)
def get_appointment(appointment_id: str, db: Session = Depends(get_db)):
    record = crud.get_appointment(db, appointment_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Appointment '{appointment_id}' not found."
        )
    return {"data": _serialize(record), "error": None}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(appointment_in: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, appointment_in.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{appointment_in.patient_id}' not found.",
        )

    payload = appointment_in.model_dump(mode="json")
    logger.info("Collected appointment payload: %s", payload)

    record = crud.create_appointment(db, appointment_in)
    return {"data": _serialize(record), "error": None}
