from datetime import date, timedelta

import pytest

from app import models
from app.database import SessionLocal


# ---------------------------------------------------------------------------
# POST /patients
# ---------------------------------------------------------------------------


def test_create_patient_success(client, patient_payload):
    resp = client.post("/patients", json=patient_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["patient_id"]
    assert body["data"]["first_name"] == "Ana"
    assert body["data"]["date_of_birth"] == "1990-01-15"


@pytest.mark.parametrize(
    "missing_field",
    [
        "first_name",
        "last_name",
        "date_of_birth",
        "sex",
        "phone_number",
        "address_line_1",
        "city",
        "state",
        "zip_code",
    ],
)
def test_create_patient_missing_required_field_returns_422(client, patient_payload, missing_field):
    payload = dict(patient_payload)
    del payload[missing_field]

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 422
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_create_patient_future_date_of_birth_returns_422(client, patient_payload):
    future_dob = (date.today() + timedelta(days=1)).strftime("%m/%d/%Y")
    payload = {**patient_payload, "date_of_birth": future_dob}

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 422


def test_create_patient_invalid_phone_returns_422(client, patient_payload):
    payload = {**patient_payload, "phone_number": "12345"}

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 422


def test_create_patient_invalid_state_returns_422(client, patient_payload):
    payload = {**patient_payload, "state": "ZZ"}

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 422


def test_create_patient_invalid_zip_returns_422(client, patient_payload):
    payload = {**patient_payload, "zip_code": "not-a-zip"}

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 422


def test_create_patient_invalid_name_characters_returns_422(client, patient_payload):
    payload = {**patient_payload, "first_name": "Ana123"}

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 422


def test_create_patient_accepts_mm_dd_yyyy_date_format(client, patient_payload):
    payload = {**patient_payload, "date_of_birth": "04/12/1988"}

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 201
    assert resp.json()["data"]["date_of_birth"] == "1988-04-12"


def test_create_patient_empty_optional_fields_become_null(client, patient_payload):
    payload = {
        **patient_payload,
        "email": "",
        "address_line_2": "",
        "insurance_provider": "",
        "insurance_member_id": "",
        "emergency_contact_name": "",
        "emergency_contact_phone": "",
    }

    resp = client.post("/patients", json=payload)

    assert resp.status_code == 201
    data = resp.json()["data"]
    for field in (
        "email",
        "address_line_2",
        "insurance_provider",
        "insurance_member_id",
        "emergency_contact_name",
        "emergency_contact_phone",
    ):
        assert data[field] is None


# ---------------------------------------------------------------------------
# GET /patients
# ---------------------------------------------------------------------------


def test_list_patients_returns_all_created(client, patient_payload):
    client.post("/patients", json=patient_payload)
    client.post("/patients", json={**patient_payload, "first_name": "Bob", "phone_number": "212-555-0101"})

    resp = client.get("/patients")

    assert resp.status_code == 200
    assert resp.json()["error"] is None
    assert len(resp.json()["data"]) == 2


def test_list_patients_filter_by_last_name(client, patient_payload):
    client.post("/patients", json=patient_payload)
    client.post(
        "/patients",
        json={**patient_payload, "first_name": "Bob", "last_name": "Smith", "phone_number": "212-555-0101"},
    )

    resp = client.get("/patients", params={"last_name": "Lee"})

    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["last_name"] == "Lee"


def test_list_patients_filter_by_date_of_birth(client, patient_payload):
    client.post("/patients", json=patient_payload)
    client.post(
        "/patients",
        json={**patient_payload, "first_name": "Bob", "date_of_birth": "06/01/1975", "phone_number": "212-555-0101"},
    )

    resp = client.get("/patients", params={"date_of_birth": "1990-01-15"})

    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["first_name"] == "Ana"


def test_list_patients_filter_by_phone_number(client, patient_payload):
    client.post("/patients", json=patient_payload)
    client.post("/patients", json={**patient_payload, "first_name": "Bob", "phone_number": "212-555-0101"})

    resp = client.get("/patients", params={"phone_number": "212-555-0100"})

    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["first_name"] == "Ana"


# ---------------------------------------------------------------------------
# GET /patients/{id}
# ---------------------------------------------------------------------------


def test_get_patient_by_id_success(client, patient_payload):
    created = client.post("/patients", json=patient_payload).json()["data"]

    resp = client.get(f"/patients/{created['patient_id']}")

    assert resp.status_code == 200
    assert resp.json()["data"]["patient_id"] == created["patient_id"]


def test_get_patient_by_id_not_found_returns_404(client):
    resp = client.get("/patients/does-not-exist")

    assert resp.status_code == 404
    assert resp.json()["data"] is None


# ---------------------------------------------------------------------------
# PUT /patients/{id}
# ---------------------------------------------------------------------------


def test_update_patient_partial_update(client, patient_payload):
    created = client.post("/patients", json=patient_payload).json()["data"]

    resp = client.put(f"/patients/{created['patient_id']}", json={"city": "Brooklyn"})

    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["city"] == "Brooklyn"
    # Fields not supplied in the PUT body are left untouched.
    assert updated["first_name"] == created["first_name"]
    assert updated["last_name"] == created["last_name"]
    assert updated["address_line_1"] == created["address_line_1"]
    # updated_at advances even though only one field changed.
    assert updated["updated_at"] != created["updated_at"]
    assert updated["created_at"] == created["created_at"]


def test_update_patient_not_found_returns_404(client):
    resp = client.put("/patients/does-not-exist", json={"city": "Brooklyn"})

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /patients/{id}
# ---------------------------------------------------------------------------


def test_delete_patient_soft_deletes(client, patient_payload):
    created = client.post("/patients", json=patient_payload).json()["data"]
    patient_id = created["patient_id"]

    resp = client.delete(f"/patients/{patient_id}")

    assert resp.status_code == 200
    deleted = resp.json()["data"]
    assert deleted["deleted_at"] is not None

    # No longer served by the list or single-record endpoints.
    list_resp = client.get("/patients")
    assert all(p["patient_id"] != patient_id for p in list_resp.json()["data"])

    get_resp = client.get(f"/patients/{patient_id}")
    assert get_resp.status_code == 404


def test_delete_patient_is_soft_delete_not_hard_delete(client, patient_payload):
    created = client.post("/patients", json=patient_payload).json()["data"]
    patient_id = created["patient_id"]

    client.delete(f"/patients/{patient_id}")

    db = SessionLocal()
    try:
        record = db.query(models.Patient).filter(models.Patient.patient_id == patient_id).first()
        assert record is not None, "row should still exist in the database after a soft delete"
        assert record.deleted_at is not None
    finally:
        db.close()


def test_delete_patient_not_found_returns_404(client):
    resp = client.delete("/patients/does-not-exist")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /patients/lookup (and the /patients/lookup/{phone_number} path variant)
# ---------------------------------------------------------------------------


def test_lookup_by_query_param_returns_matching_patient(client, patient_payload):
    client.post("/patients", json=patient_payload)

    resp = client.get("/patients/lookup", params={"phone_number": patient_payload["phone_number"]})

    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["phone_number"] == "2125550100"


def test_lookup_by_query_param_no_match_returns_null_data(client):
    resp = client.get("/patients/lookup", params={"phone_number": "212-555-9999"})

    assert resp.status_code == 200
    assert resp.json() == {"data": None, "error": None}


def test_lookup_excludes_soft_deleted_patients(client, patient_payload):
    created = client.post("/patients", json=patient_payload).json()["data"]
    client.delete(f"/patients/{created['patient_id']}")

    resp = client.get("/patients/lookup", params={"phone_number": patient_payload["phone_number"]})

    assert resp.status_code == 200
    assert resp.json() == {"data": None, "error": None}


def test_lookup_by_path_param_matches_query_param_behavior(client, patient_payload):
    client.post("/patients", json=patient_payload)

    resp = client.get(f"/patients/lookup/{patient_payload['phone_number']}")

    assert resp.status_code == 200
    assert resp.json()["data"]["phone_number"] == "2125550100"
