# tests/unit/test_api_contract.py
def test_predict_success(client, valid_payload):
    res = client.post("/api/predict", json=valid_payload)

    assert res.status_code == 200

    data = res.json()
    assert "label" in data
    assert "confidence" in data

    assert data["label"] == "no"
    assert 0.0 <= data["confidence"] <= 1.0
