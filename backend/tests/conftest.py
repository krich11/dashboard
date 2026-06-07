import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"
os.environ["MOCK_MODE"] = "true"
os.environ["MOCK_SCENARIO"] = "all_clear"
os.environ["TESTING"] = "true"
os.environ["DASHBOARD_SECRET_KEY"] = "test-secret-key-for-encryption"

from app.config import get_settings

get_settings.cache_clear()

from app.db.base import Base
import app.db.session as db_session

engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session.engine = engine
db_session.SessionLocal = TestingSessionLocal

from app.db.session import get_db
from app.main import app
from app.services.seed import seed_from_mocks


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_from_mocks(db)
    db.close()
    yield