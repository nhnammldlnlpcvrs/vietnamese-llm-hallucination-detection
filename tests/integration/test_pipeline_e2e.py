# tests/integration/test_pipeline_e2e.py
import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_pipeline_stability_multiple_runs(model):
    labels = []

    for _ in range(3):
        result = model.predict(
            context="Việt Nam nằm ở Đông Nam Á.",
            prompt="Việt Nam nằm ở đâu?",
            response="Việt Nam nằm ở Đông Nam Á."
        )
        labels.append(result["label"])

    assert len(set(labels)) == 1