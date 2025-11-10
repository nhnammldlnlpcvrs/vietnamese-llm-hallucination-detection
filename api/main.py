from utils.logger import logger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from prometheus_client import Counter, Histogram, start_http_server
import time
from transformers import AutoTokenizer
from utils.model_arch import CafeBERTNLIClassifier

# Prometheus metrics
REQUEST_COUNT = Counter('api_request_count', 'Total number of API requests', ['endpoint'])
REQUEST_LATENCY = Histogram('api_request_latency_seconds', 'Request latency', ['endpoint'])
start_http_server(8001)  # Prometheus metrics port

# FastAPI app
app = FastAPI(title="ViHallu API")

# Load tokenizer + model
MODEL_PATH = "model/best_cafebase_nli.pt"
TOKENIZER_NAME = "uitnlp/CafeBERT"
SPECIAL_TOKENS = ["<PROMPT>", "</PROMPT>", "<CONTEXT>", "</CONTEXT>", "<RESPONSE>", "</RESPONSE>"]

try:
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
    tokenizer.add_special_tokens({"additional_special_tokens": SPECIAL_TOKENS})
    logger.info("Tokenizer loaded and special tokens added")

    # Tạo model
    ckpt = torch.load(MODEL_PATH, map_location="cpu")
    num_labels = len(ckpt["label2id"])
    model = CafeBERTNLIClassifier(num_labels=num_labels)

    # Resize embeddings theo tokenizer
    model.base.resize_token_embeddings(len(tokenizer))

    # Load state_dict
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    logger.info(f"Loaded model from {MODEL_PATH} successfully")

except Exception as e:
    logger.error(f"Failed to load model: {e}")
    model = None

# Pydantic request/response
class PredictRequest(BaseModel):
    text1: str
    text2: str

class PredictResponse(BaseModel):
    label: str
    score: float

# Health check
@app.get("/health")
def health():
    return {"status": "healthy"}

# Prediction endpoint
@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    start_time = time.time()
    REQUEST_COUNT.labels(endpoint="/predict").inc()

    try:
        # Tokenize inputs
        encoded = tokenizer(
            req.text1,
            req.text2,
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt"
        )

        input_ids = encoded["input_ids"]
        attention_mask = encoded["attention_mask"]

        with torch.no_grad():
            logits = model(input_ids, attention_mask)
            scores = torch.softmax(logits, dim=1)
            score, pred_id = torch.max(scores, dim=1)
            label = list(ckpt["label2id"].keys())[pred_id.item()]

        latency = time.time() - start_time
        REQUEST_LATENCY.labels(endpoint="/predict").observe(latency)
        logger.info(f"/predict request processed in {latency:.4f}s")

        return PredictResponse(label=label, score=score.item())

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))