def test_missing_field(client):
    r = client.post("/api/predict", json={"context": "a"})
    assert r.status_code == 422


def test_wrong_type(client):
    r = client.post("/api/predict", json={
        "context": 1,
        "prompt": True,
        "response": None
    })
    assert r.status_code == 422


def test_empty_strings(client):
    r = client.post("/api/predict", json={
        "context": "",
        "prompt": "",
        "response": ""
    })
    assert r.status_code == 200