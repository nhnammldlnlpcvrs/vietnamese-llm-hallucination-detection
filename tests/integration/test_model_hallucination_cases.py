import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_no_hallucination_case(model):
    result = model.predict(
        context="Paris là thủ đô của Pháp.",
        prompt="Thủ đô của Pháp là gì?",
        response="Paris là thủ đô của Pháp."
    )
    assert result["label"] == "No Hallucination"


@pytest.mark.integration
@pytest.mark.slow
def test_intrinsic_hallucination_case(model):
    result = model.predict(
        context="Nước sôi ở 100 độ C.",
        prompt="Nước sôi ở bao nhiêu độ?",
        response="Nước sôi ở 200 độ C."
    )
    assert result["label"] == "Intrinsic Hallucination"


@pytest.mark.integration
@pytest.mark.slow
def test_extrinsic_hallucination_case(model):
    result = model.predict(
        context="Albert Einstein là nhà vật lý.",
        prompt="Albert Einstein là ai?",
        response="Albert Einstein là nhà vật lý và là tổng thống Mỹ."
    )
    assert result["label"] == "Extrinsic Hallucination"