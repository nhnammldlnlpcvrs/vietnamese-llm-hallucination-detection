import gradio as gr
import requests
import os

# Mặc định dùng API localhost, có thể thay bằng URL thật khi deploy
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/predict")

def predict_fn(context, prompt, response):
    """
    Gửi request đến backend FastAPI để dự đoán hallucination.
    """
    payload = {
        "context": context,
        "prompt": prompt,
        "response": response
    }

    try:
        r = requests.post(API_URL, json=payload, timeout=10)
        r.raise_for_status()
        result = r.json()
        return result  # ví dụ {"label": "no", "score": 0.83}
    except Exception as e:
        return {"error": str(e)}

# Tạo giao diện Gradio
iface = gr.Interface(
    fn=predict_fn,
    inputs=[
        gr.Textbox(lines=5, label="Context", placeholder="Nhập ngữ cảnh gốc..."),
        gr.Textbox(lines=3, label="Prompt", placeholder="Nhập câu hỏi / yêu cầu..."),
        gr.Textbox(lines=5, label="Response", placeholder="Nhập câu trả lời của mô hình..."),
    ],
    outputs=gr.JSON(label="Prediction Result"),
    title="ViHallu Demo - Hallucination Detection",
    description=(
        "Nhập vào 3 phần: Context, Prompt, và Response để mô hình dự đoán khả năng sinh ảo (hallucination). "
        "Kết quả trả về gồm nhãn (`extrinsic`, `intrinsic` và `no`) và xác suất tin cậy."
    )
)

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=7860, share=False)