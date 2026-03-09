from unittest.mock import MagicMock, patch

def test_model_crash(client):
    mock_model = MagicMock()
    mock_model.predict.side_effect = RuntimeError("boom")

    with patch("backend.routers.predict.get_hallu_model", return_value=mock_model):
        r = client.post("/api/predict", json={
            "context": "a",
            "prompt": "b",
            "response": "c"
        })

    assert r.status_code == 500
