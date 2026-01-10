import pytest

@pytest.mark.integration
@pytest.mark.slow
def test_model_basic_inference(model):
    result = model.predict(
        context="Hà Nội là thủ đô của Việt Nam.",
        prompt="Thủ đô Việt Nam là gì?",
        response="Thủ đô của Việt Nam là Hà Nội."
    )

    assert isinstance(result, dict)
    assert "label" in result
    assert "confidence" in result

    assert result["label"] in {
        "No Hallucination",
        "Extrinsic Hallucination",
        "Intrinsic Hallucination"
    }

    assert 0.0 <= result["confidence"] <= 1.0