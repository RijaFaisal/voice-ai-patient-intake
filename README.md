# voice-ai-patient-intake

A FastAPI backend for patient registration/intake, paired with a Vapi voice
agent ("Mira") that registers patients over a phone call. It exposes a
REST API for creating, listing, retrieving, partially updating, and
soft-deleting patient demographic records, plus scheduling and listing
appointments for those patients, with server-side validation on all
supplied fields. The deployed instance runs on Railway against a
PostgreSQL database; the same code runs locally against SQLite with zero
configuration.

## Live demo

- API base URL: https://voice-ai-patient-intake-production-e7f4.up.railway.app
- Call the voice agent: **+1 732 782 5565**

## Tech stack

| Concern         | Choice                | Why |
|------------------|------------------------|-----|
| Backend framework | FastAPI               | Fast to build, gives automatic request validation and OpenAPI/Swagger docs for free, and Pydantic integration keeps validation and serialization out of the route handlers — a good fit for a small, well-typed CRUD API. |
| Data validation  | Pydantic v2            | Declarative field constraints + custom validators map directly onto the intake rules (name characters, phone format, state codes, ZIP format, non-future DOB) and produce structured error output. |
| ORM              | SQLAlchemy 2.0         | Keeps SQL out of the route handlers, and the same model definitions work across SQLite (local dev) and PostgreSQL (deployed) with only a `DATABASE_URL` change. |
| Database         | PostgreSQL on Railway (deployed), SQLite (local) | Postgres gives the deployed app persistent, hosted storage that survives restarts and redeploys, which a container-local SQLite file would not. SQLite remains the zero-setup default for local development — see Architecture. |
| Server           | Uvicorn                | Standard ASGI server for FastAPI. |
| Voice layer      | Vapi                   | Abstracts telephony, speech-to-text, and text-to-speech behind one API/dashboard, so the voice agent only needs a system prompt and a tool definition rather than a custom telephony/STT/TTS stack. |
| LLM              | Groq — Llama 3.3 70B   | Groq's inference is fast and low-latency, which matters for a real-time voice conversation where the caller is waiting on each turn. |
| Config           | `python-dotenv` + env vars | No hardcoded secrets or paths; `.env` is gitignored, `.env.example` documents every variable. |

## Project structure

```
app/
  main.py            FastAPI app, startup table creation, exception handlers (error envelope)
  database.py        SQLAlchemy engine/session, get_db() dependency
  models.py           SQLAlchemy Patient, Appointment, CallTranscript models, Sex enum
  schemas.py          Pydantic request/response schemas + field validators
  validators.py        Reusable validation functions (name, phone, state, zip, DOB)
  crud.py              DB access functions (list/get/create/update/soft-delete)
  routers/
    patients.py        The /patients endpoints
    appointments.py     The /appointments endpoints
    call_transcripts.py  The /call-transcripts endpoints
    vapi.py              The Vapi end-of-call-report webhook
seed.py                 Inserts 1-2 sample patient records
tests/
  conftest.py          Test-DB override + shared fixtures (client, patient_payload)
  test_patients.py      Integration tests for the /patients endpoints
requirements.txt
requirements-dev.txt    Adds pytest + httpx for running the test suite
.env.example
```

### Architecture

The system is four distinct layers. Each is independently swappable — the
API doesn't know it's being called by a phone call rather than curl, and
the voice agent doesn't know or care whether the API is backed by Postgres
or SQLite:

```
Caller (phone)
   │
   ▼
1. Telephony / STT / TTS  —  Vapi
   │  (text turns only, in and out)
   ▼
2. LLM / conversation  —  Groq (Llama 3.3 70B), driven by voice/prompt.md
   │  (calls the save_patient tool once the caller confirms)
   ▼
3. API  —  this FastAPI backend (this repo)
   │  router -> Pydantic schema (validation) -> crud.py (SQLAlchemy)
   ▼
4. Database  —  PostgreSQL on Railway (deployed) / SQLite (local)
```

1. **Telephony layer — Vapi.** Vapi answers the call and handles speech-to-
   text and text-to-speech, so the LLM layer only ever deals in text turns.
   There's no custom telephony/STT/TTS code in this repo.
2. **LLM layer — Groq, Llama 3.3 70B.** The conversation is driven entirely
   by the system prompt in [`voice/prompt.md`](voice/prompt.md) — it
   defines what Mira collects, how she validates and confirms, and that she
   must call the `save_patient` tool once the caller confirms. This layer
   is config (the prompt + the Vapi tool definition pointed at this API),
   not code in this repo.
3. **API layer — this FastAPI backend.** Vapi's `save_patient` tool call
   reaches this service as `POST /patients`, going through the same
   request flow as any other client: `router -> Pydantic schema
   (validation) -> crud.py (SQLAlchemy) -> database`.
4. **Database layer — PostgreSQL on Railway, SQLite locally.** The FastAPI
   backend runs as a Railway service; persistence is a Railway-managed
   PostgreSQL database. `app/database.py` reads the connection string from
   the `DATABASE_URL` environment variable (which Railway's Postgres
   plugin injects automatically) and falls back to a local SQLite file
   (`sqlite:///./patient_intake.db`) when `DATABASE_URL` is unset, so the
   same code runs against Postgres in production and SQLite locally with no
   code changes. It also rewrites a legacy `postgres://` URL scheme to
   `postgresql://`, which SQLAlchemy 2.0 requires.

Within the API layer:

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

`Appointment` (table `appointments`):

| Field | Required | Notes |
|---|---|---|
| `appointment_id` | auto | UUID v4, primary key, server-generated |
| `patient_id` | **yes** | foreign key to `patients.patient_id`; must reference an existing, non-deleted patient |
| `appointment_date` | **yes** | ISO 8601 date-time (e.g. `2026-10-01T14:30:00`); cannot be in the past |
| `reason` | no | free text, up to 255 characters |
| `created_at` | auto | set on insert |
| `deleted_at` | auto | `null` unless soft-deleted |

`CallTranscript` (table `call_transcripts`):

| Field | Required | Notes |
|---|---|---|
| `transcript_id` | auto | UUID v4, primary key, server-generated |
| `patient_id` | no | foreign key to `patients.patient_id`; auto-set by matching `phone_number` to an active patient, `null` if no match or no phone given |
| `phone_number` | no | any common US format accepted and normalized like elsewhere; non-US/unrecognized numbers from the Vapi webhook are stored as-is (see Known limitations) |
| `transcript` | **yes** | full call transcript text |
| `summary` | no | call summary text, if available |
| `created_at` | auto | set on insert |

No soft-delete on this table — transcripts aren't user-editable or deletable through the API.

## Voice agent

The Vapi voice agent, Mira, handles patient registration by phone: it
greets the caller, collects the required demographics conversationally
(one or two fields at a time, reading back phone numbers, ZIP codes, and
dates to confirm), then offers the optional fields (email, insurance,
preferred language, emergency contact) as a group and only collects what
the caller opts into. Before saving, it reads back everything it collected
and asks the caller to confirm. Only after explicit confirmation does it
call the `save_patient` tool, which sends a `POST /patients` request to
this backend with the collected fields. On success it confirms registration
to the caller and ends the call; on failure it apologizes and tells the
caller to try again shortly, without claiming success.

The full system prompt is in [`voice/prompt.md`](voice/prompt.md).

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

Environment variables (see `.env.example`):

- `DATABASE_URL` — **required in production.** SQLAlchemy connection string.
  On Railway this is provided automatically by the attached Postgres
  service; locally it's optional and defaults to a local SQLite file
  (`sqlite:///./patient_intake.db`) when unset.
- `APP_ENV`, `LOG_LEVEL`, `HOST`, `PORT` — optional, all have sane defaults
  for local development.

No secrets are required to run this service locally.

## Running tests

Integration tests for the `/patients` endpoints live in `tests/`, using
pytest and FastAPI's `TestClient`. They run against a private, temp-file
SQLite database created fresh for the test session — `tests/conftest.py`
overrides `DATABASE_URL` before the app is imported, so tests never touch
production Postgres or a developer's local SQLite file, and each test gets
a clean schema.

```bash
pip install -r requirements-dev.txt   # adds pytest + httpx on top of requirements.txt
pytest
```

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

### `GET /patients/lookup`
Look up an active (non-deleted) patient by phone number. Query param
`phone_number` is required and accepts any format the phone validator
accepts. → `200` with `data` set to the matching patient, or `data: null` if
no patient has that phone number (not a `404` — this lets callers
distinguish "no match" from an error). `400` if `phone_number` fails
validation.

### `GET /patients/lookup/{phone_number}`
Path-parameter equivalent of `GET /patients/lookup` — same lookup, same
response shape, same `400`/`200`-with-`null` behavior. Defined before
`GET /patients/{patient_id}` so `lookup` is never captured as a
`patient_id`.

### `GET /appointments`
Lists non-deleted appointments, ordered by `appointment_date`. Optional
query filter: `patient_id`. → `200`, `data` is an array.

### `GET /appointments/{appointment_id}`
→ `200` with the appointment, or `404` if not found or soft-deleted.

### `POST /appointments`
Body: `patient_id` (must reference an existing, non-deleted patient) and
`appointment_date` (ISO 8601, cannot be in the past); `reason` is optional.
→ `201` with the created appointment, `404` if `patient_id` doesn't match
an existing patient, or `422` on validation failure (e.g. a past date).

```bash
curl -X POST http://127.0.0.1:8000/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "<existing patient_id>",
    "appointment_date": "2026-10-01T14:30:00",
    "reason": "Annual checkup"
  }'
```

### `GET /call-transcripts`
Lists all stored call transcripts, most recent first. Optional query
filter: `patient_id`. → `200`, `data` is an array.

### `POST /call-transcripts`
Body: `transcript` (required), `summary` (optional), `phone_number`
(optional). If `phone_number` is given, it's validated/normalized the same
way as everywhere else, and `patient_id` is auto-set by looking up an
active patient with that phone number (`null` if none matches). → `201`
with the created record, or `422` on validation failure (missing
transcript, malformed phone number).

```bash
curl -X POST http://127.0.0.1:8000/call-transcripts \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "AI: Hello. Caller: Hi, I would like to confirm my appointment.",
    "summary": "Caller confirmed their upcoming appointment.",
    "phone_number": "415-555-0132"
  }'
```

### `POST /vapi/webhook`
Server-message webhook for Vapi. Point a Vapi assistant's server URL at
this endpoint. Vapi posts every call event (status updates, transcript
chunks, the end-of-call report, etc.) to the same URL, each wrapped as
`{ "message": { "type": ..., ... } }`; this endpoint only acts on
`type: "end-of-call-report"` and acknowledges (`200`, `data: null`) every
other event type without storing anything.

For an end-of-call report, it extracts the transcript (`message.transcript`
or `message.artifact.transcript`), the summary (`message.summary` or
`message.analysis.summary`), and the caller's number
(`message.customer.number` or `message.call.customer.number`), then stores
them via the same lookup-and-link logic as `POST /call-transcripts`. →
`200` with the created record. `400` if no transcript is present in the
report. A phone number that doesn't fit the US phone format (e.g. a
non-US E.164 number) is stored as-is on the record without patient
matching, rather than failing the whole webhook call.

## Known limitations

- **No auth on the Vapi webhook.** `POST /vapi/webhook` accepts any request
  matching the expected shape — there's no shared-secret or signature check
  against the caller. Vapi supports a server-URL secret; add verification
  of it before relying on this in a setting where the endpoint is
  discoverable.
- **No update/delete for call transcripts.** `POST` and `GET` are the only
  endpoints — transcripts can't be edited or removed through the API.
- **No update/cancel endpoint for appointments.** `POST` and the two `GET`s
  are the only appointment endpoints — there's no `PUT` to reschedule and no
  `DELETE` to cancel/soft-delete an appointment yet.
- **No double-booking check.** Creating an appointment doesn't check for
  overlapping appointments for the same patient or a shared resource
  (provider/room) — any number of appointments can be scheduled at the same
  `appointment_date`.
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
- **SQLite concurrency (local dev only).** The deployed instance uses
  PostgreSQL, not SQLite, so this doesn't affect production. SQLite is only
  used as the local-dev fallback, and it serializes writes at the file
  level — fine for single-process local use, not for concurrent multi-writer
  traffic.
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
- **Railway free-trial hosting.** The deployed instance runs on Railway's
  free trial, which is subject to a 30-day/usage-credit limit — the live
  demo URL and phone number may stop working once that's exhausted.
- **Vapi free number is inbound-only.** The demo phone number can be called
  to reach Mira, but the free Vapi number can't place outbound calls.
- **`date_of_birth` accepted in `MM/DD/YYYY`** (with `YYYY-MM-DD` also
  accepted for backward compatibility) — see Data model above; API
  consumers expecting ISO-only input should account for this.
