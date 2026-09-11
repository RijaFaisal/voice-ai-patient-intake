"""
Seed the database with sample patient records for local development and
manual testing.

Usage:
    python seed.py
"""
from datetime import date

from app import crud, schemas
from app.database import Base, SessionLocal, engine

SEED_PATIENTS = [
    schemas.PatientCreate(
        first_name="Maria",
        last_name="Gonzalez",
        date_of_birth=date(1988, 4, 12),
        sex="Female",
        phone_number="(415) 555-0132",
        email="maria.gonzalez@example.com",
        address_line_1="742 Evergreen Terrace",
        address_line_2="Apt 3B",
        city="San Francisco",
        state="ca",
        zip_code="94110",
        insurance_provider="Blue Shield of California",
        insurance_member_id="BSC-88213456",
        preferred_language="Spanish",
        emergency_contact_name="Carlos Gonzalez",
        emergency_contact_phone="415-555-0199",
    ),
    schemas.PatientCreate(
        first_name="James",
        last_name="O'Connor",
        date_of_birth=date(1975, 11, 2),
        sex="Male",
        phone_number="6175550143",
        address_line_1="10 Beacon Street",
        city="Boston",
        state="MA",
        zip_code="02108-1234",
        preferred_language="English",
    ),
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = crud.list_patients(db)
        if existing:
            print(f"Database already has {len(existing)} patient(s); skipping seed.")
            return
        for patient_in in SEED_PATIENTS:
            record = crud.create_patient(db, patient_in)
            print(f"Seeded patient {record.patient_id}: {record.first_name} {record.last_name}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
