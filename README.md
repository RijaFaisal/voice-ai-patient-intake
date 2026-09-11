# voice-ai-patient-intake

A small FastAPI backend for patient registration/intake, backed by SQLite.
It exposes a five-endpoint REST API for creating, listing, retrieving,
partially updating, and soft-deleting patient demographic records, with
server-side validation on all patient-supplied fields.

## Tech stack

| Concern         | Choice                | Why |
|------------------|------------------------|-----|
| Web framework    | FastAPI                | Async-capable, generates OpenAPI/Swagger docs for free, and Pydantic integration gives request validation and serialization with minimal boilerplate — a good fit for a small, well-typed CRUD API. |
| Data validation  | Pydantic v2            | Declarative field constraints + custom validators map directly onto the intake rules (name characters, phone format, state codes, ZIP format, non-future DOB) and produce structured error output. |
| ORM              | SQLAlchemy 2.0         | Keeps SQL out of the route handlers, and the same model definitions work if the project later moves off SQLite (e.g. to Postgres) with only a `DATABASE_URL` change. |
| Database         | SQLite                 | Zero-setup, file-based, sufficient for a single-service intake backend or local/dev use, as requested. Not a concurrency-heavy production choice — see Known Limitations. |
| Server           | Uvicorn                | Standard ASGI server for FastAPI. |
| Config           | `python-dotenv` + env vars | No hardcoded secrets or paths; `.env` is gitignored, `.env.example` documents every variable. |

## Project structure

```
app/
  main.py            FastAPI app, startup table creation, exception handlers (error envelope)
  database.py        SQLAlchemy engine/session, get_db() dependency
  models.py           SQLAlchemy Patient model + Sex enum
  schemas.py          Pydantic request/response schemas + field validators
  validators.py        Reusable validation functions (name, phone, state, zip, DOB)
  crud.py              DB access functions (list/get/create/update/soft-delete)
  routers/
    patients.py        The five /patients endpoints
seed.py                 Inserts 1-2 sample patient records
requirements.txt
.env.example
```

### Architecture

Request flow: `router -> Pydantic schema (validation) -> crud.py (SQLAlchemy) -> SQLite`.

- **Validation lives in one place.** `app/validators.py` holds the regex/logic
  for names, phone numbers, state codes, ZIP codes, and date-of-birth
  plausibility. `app/schemas.py` wires these into `PatientCreate` (all
  required fields enforced) and `PatientUpdate` (all fields optional, but
  validated with the same rules when present) via Pydantic
  `field_validator`s. The `GET /patients` phone filter reuses
  `validators.validate_phone` directly so filtering and creation normalize
  phone numbers identically.
- **Errors are normalized centrally.** `app/main.py` registers exception
  handlers for Pydantic validation errors, `HTTPException` (404s, explicit
  400s), SQLAlchemy errors, and any unhandled exception, so every response —
  success or failure — uses the same `{ "data": ..., "error": ... }`
  envelope and consistent HTTP status codes.
- **Soft delete only.** `DELETE /patients/{id}` sets `deleted_at`; no code
  path issues a `DELETE FROM patients`. All reads (`GET /patients`,
  `GET /patients/{id}`, and the filters) exclude rows where `deleted_at IS
  NOT NULL`.
- **Payload logging.** `POST` and `PUT` log the fully validated/normalized
  payload to stdout via the standard `logging` module before writing to the
  database (see Known Limitations re: PII in logs).

## Data model

`Patient` (table `patients`):

| Field | Required | Notes |
|---|---|---|
| `patient_id` | auto | UUID v4, primary key, server-generated |
| `first_name` | **yes** | letters/space/hyphen/apostrophe/period, 1–50 chars |
| `last_name` | **yes** | same rules as `first_name` |
| `date_of_birth` | **yes** | accepted input format is `MM/DD/YYYY` (e.g. `04/12/1988`); `YYYY-MM-DD` is also accepted for backward compatibility. Cannot be in the future, must be ≤150 years ago. Stored internally as a proper `DATE` column and returned in responses as ISO `YYYY-MM-DD`. |
| `sex` | **yes** | enum: `Male`, `Female`, `Other`, `Decline to Answer` |
| `phone_number` | **yes** | any common US format accepted, normalized/stored as 10 digits |
| `address_line_1` | **yes** | |
| `city` | **yes** | |
| `state` | **yes** | 2-letter USPS state/territory abbreviation, case-insensitive input, stored uppercase |
| `zip_code` | **yes** | `12345` or `12345-6789` |
| `email` | no | validated as RFC email if present |
| `address_line_2` | no | |
| `insurance_provider` | no | self-pay patients may have none |
| `insurance_member_id` | no | |
| `preferred_language` | no | defaults to `"English"` |
| `emergency_contact_name` | no | same character rules as name fields when present |
| `emergency_contact_phone` | no | same phone rules when present |
| `created_at` | auto | set on insert |
| `updated_at` | auto | set on insert and every update (including soft-delete) |
| `deleted_at` | auto | `null` unless soft-deleted |

**Required-field rationale:** identity (name, DOB, sex), one reachable phone
number, and a mailing address are the fields a US ambulatory intake form
needs to register and bill a patient. Email, insurance (self-pay patients
have none), preferred language, and emergency contact are commonly collected
but not blocking, so they're optional.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # defaults work as-is for local SQLite use

python seed.py          # optional: inserts 2 sample patients

uvicorn app.main:app --reload
```

The API is now at `http://127.0.0.1:8000`, interactive docs at
`http://127.0.0.1:8000/docs`, and a health check at `/health`.

Environment variables (see `.env.example`): `DATABASE_URL` (SQLAlchemy URL,
defaults to a local SQLite file), `APP_ENV`, `LOG_LEVEL`, `HOST`, `PORT`.
No secrets are required to run this service locally.

## API

All responses use the envelope `{ "data": ..., "error": ... }` — exactly one
of the two is non-null. Validation errors return `422` with a `details`
array of `{ field, message }`; not-found returns `404`; a malformed filter
value (e.g. unparsable phone) returns `400`.

### `GET /patients`
Lists non-deleted patients. Optional query filters: `last_name` (exact,
case-insensitive), `date_of_birth` (`YYYY-MM-DD`), `phone_number` (any
format accepted by the phone validator, normalized before matching).
→ `200`, `data` is an array.

### `GET /patients/{patient_id}`
→ `200` with the patient, or `404` if not found or soft-deleted.

### `POST /patients`
Body: all required fields plus any optional fields. → `201` with the
created patient, or `422` on validation failure.

```bash
curl -X POST http://127.0.0.1:8000/patients \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Ana", "last_name": "Lee",
    "date_of_birth": "01/15/1990", "sex": "Female",
    "phone_number": "212-555-0100",
    "address_line_1": "1 Main St", "city": "New York",
    "state": "NY", "zip_code": "10001"
  }'
```

### `PUT /patients/{patient_id}`
Partial update — send only the fields to change; omitted fields are left
untouched. Each supplied field is validated with the same rules as `POST`.
→ `200` with the updated patient, or `404` / `422`.

### `DELETE /patients/{patient_id}`
Soft-delete: sets `deleted_at` (and `updated_at`); the row is never removed
from the database. → `200` with the now-deleted patient record, or `404`.

## Known limitations

- **No authentication/authorization.** There's no auth layer, so this is not
  deployable as-is against real patient data. A production deployment
  handling PHI needs an auth scheme (e.g. OAuth2/JWT), audit logging of who
  accessed/changed what, and TLS in front of it, plus a signed BAA if
  hosted, for HIPAA compliance.
- **PII in application logs.** Collected payloads (including phone, address,
  insurance IDs) are logged to stdout in full, per the stated requirement.
  In a real deployment, logs containing PHI need access controls, redaction
  of sensitive fields, and a retention policy — don't ship these logs to an
  unrestricted log aggregator as-is.
- **SQLite concurrency.** SQLite serializes writes at the file level, which
  is fine for a single-process dev/demo service but not for concurrent
  multi-writer production traffic. Swapping `DATABASE_URL` to Postgres/MySQL
  is the intended upgrade path; the SQLAlchemy models don't need to change.
- **No schema migrations.** Tables are created with
  `Base.metadata.create_all()` on startup, which is fine for SQLite/dev but
  won't safely evolve a production schema. Add Alembic before making
  post-launch schema changes.
- **US-only validation.** Phone, state, and ZIP validation assume a US
  patient population, per the stated requirements; they will reject
  otherwise-valid international values.
- **`last_name` filter is exact-match**, not a substring/fuzzy search — a
  typo or partial name won't find a record.
- **No pagination** on `GET /patients` — fine for a small demo dataset, but
  needed before this scales to a large patient population.
