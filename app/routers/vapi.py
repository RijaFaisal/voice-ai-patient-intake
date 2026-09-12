import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import crud, schemas, validators
from ..database import get_db

router = APIRouter(prefix="/vapi", tags=["vapi"])
logger = logging.getLogger("patient_api")


def _serialize(record) -> dict:
    return schemas.CallTranscriptOut.model_validate(record).model_dump(mode="json")


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    message = payload.get("message", payload) if isinstance(payload, dict) else {}

    if message.get("type") not in (None, "end-of-call-report"):
        # Vapi posts other server-message types (status-update, transcript,
        # hang, etc.) to the same URL; acknowledge and ignore anything that
        # isn't the end-of-call report we store.
        return {"data": None, "error": None}

    artifact = message.get("artifact") or {}
    analysis = message.get("analysis") or {}
    transcript = message.get("transcript") or artifact.get("transcript")
    summary = message.get("summary") or analysis.get("summary")

    call = message.get("call") or {}
    customer = message.get("customer") or call.get("customer") or {}
    phone_number = customer.get("number")

    if not transcript or not str(transcript).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transcript found in end-of-call-report payload.",
        )

    normalized_phone = None
    if phone_number:
        try:
            normalized_phone = validators.validate_phone(phone_number, "phone_number")
        except ValueError:
            # Vapi customer numbers are typically E.164; if one doesn't fit
            # our US-only format, keep the raw value for the record but skip
            # patient matching rather than failing the whole webhook call.
            normalized_phone = str(phone_number).strip() or None

    # Caller ID is null for Vapi web calls, and may simply be wrong/unmatched
    # otherwise. Fall back to scanning the transcript text itself for a
    # phone number the caller stated out loud, and use that to find/link the
    # patient instead.
    patient = crud.get_patient_by_phone(db, normalized_phone) if normalized_phone else None
    if patient is None:
        candidates = validators.extract_phone_candidates(str(transcript))
        for candidate in candidates:
            candidate_patient = crud.get_patient_by_phone(db, candidate)
            if candidate_patient is not None:
                normalized_phone = candidate
                patient = candidate_patient
                break
        else:
            if candidates and not normalized_phone:
                normalized_phone = candidates[0]

    logger.info(
        "Received Vapi end-of-call-report (phone_number=%s, patient_id=%s)",
        normalized_phone,
        patient.patient_id if patient else None,
    )

    record = crud.record_call_transcript(
        db,
        transcript=str(transcript).strip(),
        summary=str(summary).strip() if summary else None,
        phone_number=normalized_phone,
    )
    return {"data": _serialize(record), "error": None}
