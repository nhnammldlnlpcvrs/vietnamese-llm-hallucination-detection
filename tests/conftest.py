# tests/conftest.py
import sys
import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def client(monkeypatch):
    """
    FastAPI TestClient with mocked model.
    Model MUST be mocked before app import.
    """
    fake_model = MagicMock()
    fake_model.predict.return_value = {
        "label": "no",
        "confidence": 0.99,
        "type": "none"
    }

    monkeypatch.setattr(
        "backend.routers.predict.hallu_model",
        fake_model,
        raising=False
    )

    from backend.main import app
    return TestClient(app)


@pytest.fixture
def mock_model(monkeypatch):
    """
    Mock hallucination model (unit tests only).
    """
    fake_model = MagicMock()
    fake_model.predict.return_value = {
        "label": "no",
        "confidence": 0.99,
        "type": "none"
    }

    monkeypatch.setattr(
        "backend.routers.predict.hallu_model",
        fake_model
    )

    return fake_model


@pytest.fixture(scope="session")
def real_model():
    """
    Load REAL hallucination model.
    VERY SLOW – integration tests only.
    """
    from backend.model.inference_model import hallu_model
    return hallu_model


# Alias cho test integration (đúng tên test đang dùng)
@pytest.fixture(scope="session")
def model(real_model):
    """
    Alias for integration tests.
    """
    return real_model


@pytest.fixture(scope="session")
def predict_fn(model):
    """
    Direct model inference (no API).
    Used in model-level integration tests.
    """

    def _predict(*, context, prompt=None, response):
        return model.predict(
            context=context,
            prompt=prompt,
            response=response
        )

    return _predict


@pytest.fixture
def valid_payload():
    return {
        "context": "Paris is the capital of France.",
        "prompt": "What is the capital of France?",
        "response": "Paris"
    }