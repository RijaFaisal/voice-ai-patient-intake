import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/call-transcripts", tags=["call-transcripts"])
logger = logging.getLogger("patient_api")


def _serialize(record) -> dict:
    return schemas.CallTranscriptOut.model_validate(record).model_dump(mode="json")


@router.get("", status_code=status.HTTP_200_OK)
def list_call_transcripts(
    patient_id: Optional[str] = Query(None, description="Filter by patient_id"),
    db: Session = Depends(get_db),
):
    records = crud.list_call_transcripts(db, patient_id=patient_id)
    return {"data": [_serialize(r) for r in records], "error": None}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_call_transcript(payload: schemas.CallTranscriptCreate, db: Session = Depends(get_db)):
    logger.info("Collected call transcript payload: %s", payload.model_dump(mode="json"))

    record = crud.record_call_transcript(
        db, transcript=payload.transcript, summary=payload.summary, phone_number=payload.phone_number
    )
    return {"data": _serialize(record), "error": None}
