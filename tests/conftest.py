import pytest
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from app.core.config.settings import Settings

load_dotenv()

GMAIL_ADDRESS=os.getenv("GMAIL_ADDRESS")
GMAIL_PASSWORD=os.getenv("GMAIL_PASSWORD")

@pytest.fixture
def mock_settings()->Settings:
    return Settings(
        GMAIL_ADDRESS=GMAIL_ADDRESS,
        GMAIL_PASSWORD=GMAIL_PASSWORD,
    )

@pytest.fixture
def client(mock_settings: Settings)->None:
    from app.main import app
    from app.core.config.settings import get_settings

    #override settings dependency
    app.dependency_overrides[get_settings] = lambda: mock_settings
    with TestClient(app) as test_client:
        yield test_client

    #cleanup
    app.dependency_overrides.clear()

