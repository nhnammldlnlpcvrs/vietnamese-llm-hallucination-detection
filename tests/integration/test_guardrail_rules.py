import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_guardrail_force_intrinsic_by_contradiction(model):
    result = model.predict(
        context="Con mèo là động vật.",
        prompt="Con mèo là gì?",
        response="Con mèo là một loại xe hơi."
    )

    assert result["label"] == "Intrinsic Hallucination"


@pytest.mark.integration
@pytest.mark.slow
def test_guardrail_force_extrinsic_by_new_entity(model):
    result = model.predict(
        context="Việt Nam có thủ đô là Hà Nội.",
        prompt="Thủ đô Việt Nam là gì?",
        response="Thủ đô Việt Nam là Hà Nội và là nơi đặt trụ sở NASA."
    )

    assert result["label"] == "Extrinsic Hallucination"