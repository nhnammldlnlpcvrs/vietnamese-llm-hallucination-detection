# tests/integration/test_model_confidence.py
import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_confidence_no_hallu_high(model):
    result = model.predict(
        context="Trái Đất quay quanh Mặt Trời.",
        prompt="Trái Đất quay quanh gì?",
        response="Trái Đất quay quanh Mặt Trời."
    )

    assert result["label"] == "no"
    assert result["confidence"] > 0.5


@pytest.mark.integration
@pytest.mark.slow
def test_confidence_intrinsic_non_trivial(model):
    result = model.predict(
        context="Mặt Trời mọc ở hướng Đông.",
        prompt="Mặt Trời mọc ở đâu?",
        response="Mặt Trời mọc ở hướng Tây."
    )

    assert result["label"] == "intrinsic"
    assert result["confidence"] > 0.3