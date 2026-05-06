import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-unit-tests")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)
