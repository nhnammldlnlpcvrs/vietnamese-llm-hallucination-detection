# tests/integration/test_edge_cases.py
import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_empty_response(model):
    result = model.predict(
        context="Hà Nội là thủ đô Việt Nam.",
        prompt="Thủ đô Việt Nam là gì?",
        response=""
    )
    assert "label" in result


@pytest.mark.integration
@pytest.mark.slow
def test_empty_context(model):
    result = model.predict(
        context="",
        prompt="Việt Nam là nước nào?",
        response="Việt Nam là một quốc gia ở Đông Nam Á."
    )
    assert "label" in result