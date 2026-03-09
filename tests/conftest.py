import sys
import os
import pytest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

try:
    import torch
    import transformers
except ImportError:
    sys.modules["torch"] = MagicMock()
    sys.modules["torch.nn"] = MagicMock()
    sys.modules["torch.nn.functional"] = MagicMock()
    sys.modules["transformers"] = MagicMock()
    sys.modules["lightgbm"] = MagicMock()
    sys.modules["numpy"] = MagicMock()
    
    mock_inf_model = MagicMock()
    sys.modules["backend.model.inference_model"] = mock_inf_model
    mock_pipeline = MagicMock()
    mock_pipeline.predict.return_value = {"label": "no", "confidence": 0.99}
    mock_inf_model.get_hallu_model.return_value = mock_pipeline

from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch):
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
    fake_model = MagicMock()
    fake_model.predict.return_value = {
        "label": "no",
        "confidence": 0.99,
        "type": "none"
    }
    monkeypatch.setattr("backend.routers.predict.hallu_model", fake_model, raising=False)
    return fake_model

@pytest.fixture(scope="session")
def real_model():
    try:
        from backend.model.inference_model import get_hallu_model
        return get_hallu_model()
    except (ImportError, AttributeError):
        return MagicMock()

@pytest.fixture
def valid_payload():
    return {
        "context": "Paris is the capital of France.",
        "prompt": "What is the capital of France?",
        "response": "Paris"
    }