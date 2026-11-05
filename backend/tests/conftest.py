import os
import tempfile
from pathlib import Path
import pytest

TEST_DIR = tempfile.TemporaryDirectory(prefix="batore-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(TEST_DIR.name) / "test.db")
os.environ["APP_MODE"] = "demo"
os.environ["GEMINI_MODEL"] = "test-only-model"
os.environ["ANALYSIS_PROVIDER"] = "gemini"
os.environ["LOCAL_SEARCH_ENABLED"] = "false"
os.environ["INSTAGRAM_BROWSER_ENABLED"] = "false"
os.environ["AUTONOMOUS_DISCOVERY"] = "false"
os.environ["RESEARCH_STREAMING"] = "false"
os.environ["INVENTORY_COLLECTION_ENABLED"] = "false"

from app.db import Base, engine
from app.main import app
from fastapi.testclient import TestClient


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    TEST_DIR.cleanup()


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client):
    token = client.post("/api/auth/demo").json()["access_token"]
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def request_data():
    return {
        "query": "sushi",
        "start_label": "RS Puram",
        "lat": 11.008,
        "lng": 76.948,
        "departure": "2026-11-05T17:00:00+05:30",
        "duration_minutes": 180,
        "party_size": 2,
        "budget": 2400,
        "budget_unit": "group",
        "transport": "drive",
        "categories": ["food", "cafe", "bowling", "gaming", "park"],
        "mood": "different",
    }
