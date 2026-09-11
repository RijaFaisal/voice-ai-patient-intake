"""
Shared pytest fixtures for the API test suite.

The DATABASE_URL override below must run before app.database (and
therefore app.main) is ever imported, so every test in this suite runs
against a private temp-file SQLite database instead of whatever
DATABASE_URL is set to in the real environment (production Postgres on
Railway, or a developer's local SQLite file). Keep this at the top of the
file, ahead of any `from app...` import.
"""
import atexit
import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(prefix="patient_intake_test_", suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
atexit.register(lambda: os.path.exists(_db_path) and os.remove(_db_path))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_database():
    """Give every test a fresh, empty schema on the private test database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def patient_payload():
    """A valid POST /patients body. Tests override individual fields with {**patient_payload, ...}."""
    return {
        "first_name": "Ana",
        "last_name": "Lee",
        "date_of_birth": "01/15/1990",
        "sex": "Female",
        "phone_number": "212-555-0100",
        "address_line_1": "1 Main St",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
    }
