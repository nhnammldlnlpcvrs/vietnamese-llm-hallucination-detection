import pytest
import requests

API_URL = "http://127.0.0.1:8000/predict"

@pytest.mark.parametrize(
    "context, prompt, response, expected_labels",
    [
        (
            "Hà Nội là thủ đô của Việt Nam. Thành phố này có Hồ Gươm và Lăng Chủ tịch Hồ Chí Minh.",
            "Thủ đô của Việt Nam là gì?",
            "Thủ đô của Việt Nam là Tokyo.",
            ["extrinsic"],
        ),
        (
            "Trái đất quay quanh Mặt Trời. Mặt Trăng quay quanh Trái đất.",
            "Mặt Trăng quay quanh hành tinh nào?",
            "Mặt Trăng quay quanh Mặt Trời.",
            ["intrinsic"],
        ),
        (
            "Albert Einstein là nhà vật lý nổi tiếng với thuyết tương đối.",
            "Ai là người phát minh ra thuyết tương đối?",
            "Albert Einstein.",
            ["no"],
        ),
    ],
)
def test_predict_labels(context, prompt, response, expected_labels):
    payload = {"context": context, "prompt": prompt, "response": response}
    r = requests.post(API_URL, json=payload, timeout=30)
    assert r.status_code == 200, f"API lỗi: {r.status_code} - {r.text}"

    data = r.json()
    assert "label" in data, "Thiếu trường label"
    assert "score" in data, "Thiếu trường score"

    print(f"Prompt: {prompt}")
    print(f"Predicted: {data['label']} | Score: {data['score']:.4f}")

    assert any(lbl in data["label"].lower() for lbl in expected_labels), (
        f"Kết quả '{data['label']}' không thuộc nhóm {expected_labels}"
    )