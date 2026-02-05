import os
import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

PHOBERT_MODEL = "vinai/phobert-base"
DEVICE = "cpu"
BATCH_SIZE = 8

DATA_PATH = "data/vihallu-dataset/vihallu-train.csv"
OUT_DIR = "features"
OUT_FILE = f"{OUT_DIR}/phobert_embeddings.npy"

os.makedirs(OUT_DIR, exist_ok=True)

def load_texts():
    df = pd.read_csv(DATA_PATH)
    texts = (
        df["context"].fillna("") + " "
        + df["prompt"].fillna("") + " "
        + df["response"].fillna("")
    ).tolist()
    return texts

def main():
    texts = load_texts()

    tokenizer = AutoTokenizer.from_pretrained(PHOBERT_MODEL)
    model = AutoModel.from_pretrained(PHOBERT_MODEL).to(DEVICE).eval()

    all_embs = []

    for i in tqdm(range(0, len(texts), BATCH_SIZE)):
        batch = texts[i:i+BATCH_SIZE]

        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt"
        )

        with torch.no_grad():
            outputs = model(**inputs)
            emb = outputs.last_hidden_state.mean(dim=1)

        all_embs.append(emb.cpu().numpy())

        del inputs, outputs, emb
        torch.cuda.empty_cache()

    X = np.vstack(all_embs)
    np.save(OUT_FILE, X)

    print(f"Saved embeddings to {OUT_FILE}, shape={X.shape}")

if __name__ == "__main__":
    main()