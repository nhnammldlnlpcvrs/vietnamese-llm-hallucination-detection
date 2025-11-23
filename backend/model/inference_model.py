import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class HalluModel:
    def __init__(self):
        model_path = os.getenv("MODEL_PATH", "models/phobert_finetuned_model")

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()

        self.labels = ["no", "intrinsic", "extrinsic"]

    def predict(self, context, prompt, response):
        text = (
            f"[CONTEXT] {context}\n"
            f"[PROMPT] {prompt}\n"
            f"[RESPONSE] {response}"
        )
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)

        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0]

        label_id = torch.argmax(probs).item()
        return {
            "label": self.labels[label_id],
            "confidence": float(probs[label_id])
        }

hallu_model = HalluModel()