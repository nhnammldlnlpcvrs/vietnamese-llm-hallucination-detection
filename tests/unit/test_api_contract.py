def test_predict_success(client, valid_payload):
    r = client.post("/api/predict", json=valid_payload)
    assert r.status_code == 200

    data = r.json()
    assert "label" in data
    assert "confidence" in data
    assert isinstance(data["confidence"], float)