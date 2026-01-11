# tests/unit/test_error_handling.py
def test_model_crash(client, monkeypatch):
    from backend.routers import predict

    def crash(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(predict.hallu_model, "predict", crash)

    r = client.post("/api/predict", json={
        "context": "a",
        "prompt": "b",
        "response": "c"
    })

    assert r.status_code == 500
    assert "boom" in r.text