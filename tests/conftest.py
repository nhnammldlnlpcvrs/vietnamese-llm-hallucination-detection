# tests/conftest.py
import sys
import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def client():
    """
    FastAPI TestClient.
    Does NOT load real model.
    """
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def mock_model(monkeypatch):
    """
    Mock hallucination model to avoid loading ML models.
    """
    fake_model = MagicMock()
    fake_model.predict.return_value = {
        "label": "No Hallucination",
        "confidence": 0.99
    }

    monkeypatch.setattr(
        "routers.predict.hallu_model",
        fake_model
    )

    return fake_model


@pytest.fixture(scope="session")
def model():
    """
    Load full hallucination pipeline.
    Integration tests ONLY.
    """
    from backend.model.inference_model import hallu_model
    return hallu_model