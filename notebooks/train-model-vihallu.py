import os
import json
import yaml
import subprocess
import mlflow
import lightgbm as lgb
import numpy as np
import torch
import pandas as pd

from transformers import AutoTokenizer, AutoModel
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score

os.environ["TORCH_DISABLE_DYNAMO"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

EXPERIMENT_NAME = "vihallu-pipeline"
PHOBERT_MODEL = "vinai/phobert-base"

NUM_FOLDS = 5
DEVICE = "cpu"
RANDOM_STATE = 42

LABEL_MAP = {
    "extrinsic": 0,
    "no": 1,
    "intrinsic": 2
}

def get_git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"]
        ).decode().strip()
    except Exception:
        return "unknown"

def load_dataset():
    path = "data/vihallu-dataset/vihallu-train.csv"
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    df = pd.read_csv(path)

    df["label"] = df["label"].astype(str).str.lower().str.strip()
    if set(df["label"]) - LABEL_MAP.keys():
        raise ValueError("Unknown labels detected")

    labels = df["label"].map(LABEL_MAP).values

    texts = (
        df["context"].fillna("") + " " +
        df["prompt"].fillna("") + " " +
        df["response"].fillna("")
    ).astype(str).tolist()

    return texts, labels

def simple_feats(text):
    return [
        len(text),
        len(text.split())
    ]

def extract_embeddings(texts, tokenizer, model, batch_size=8):
    all_embs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt"
        )
        with torch.no_grad():
            out = model(**inputs)
            emb = out.last_hidden_state.mean(dim=1)
        all_embs.append(emb.cpu().numpy())
        del inputs, out, emb
        torch.cuda.empty_cache()
    return np.vstack(all_embs)

def main():
    mlflow.set_experiment(EXPERIMENT_NAME)

    texts, y = load_dataset()

    tokenizer = AutoTokenizer.from_pretrained(PHOBERT_MODEL)
    model = AutoModel.from_pretrained(PHOBERT_MODEL).to(DEVICE).eval()

    with mlflow.start_run(run_name="vihallu-train"):

        mlflow.log_params({
            "phobert_model": PHOBERT_MODEL,
            "num_folds": NUM_FOLDS,
            "device": DEVICE,
            "git_commit": get_git_commit()
        })

        X_embed = extract_embeddings(texts, tokenizer, model)
        X_simple = np.array([simple_feats(t) for t in texts])
        X = np.hstack([X_embed, X_simple])

        skf = StratifiedKFold(
            n_splits=NUM_FOLDS,
            shuffle=True,
            random_state=RANDOM_STATE
        )

        os.makedirs("models/lgbm", exist_ok=True)
        oof_preds = np.zeros((len(y), 3))

        for fold, (tr, va) in enumerate(skf.split(X, y)):
            with mlflow.start_run(
                run_name=f"lgbm_fold_{fold}",
                nested=True
            ):
                clf = lgb.LGBMClassifier(
                    objective="multiclass",
                    num_class=3,
                    num_leaves=64,
                    learning_rate=0.05,
                    n_estimators=300
                )

                clf.fit(X[tr], y[tr])
                preds = clf.predict_proba(X[va])
                oof_preds[va] = preds

                fold_f1 = f1_score(
                    y[va],
                    np.argmax(preds, axis=1),
                    average="macro"
                )

                mlflow.log_metric("val_macro_f1", fold_f1)

                model_path = f"models/lgbm/fold_{fold}.txt"
                clf.booster_.save_model(model_path)

        oof_f1 = f1_score(
            y,
            np.argmax(oof_preds, axis=1),
            average="macro"
        )
        mlflow.log_metric("oof_macro_f1", oof_f1)

        os.makedirs("models/phobert", exist_ok=True)
        os.makedirs("models/phobert_tokenizer", exist_ok=True)

        model.save_pretrained("models/phobert")
        tokenizer.save_pretrained("models/phobert_tokenizer")

        metadata = {
            "label_map": LABEL_MAP,
            "embedding_model": PHOBERT_MODEL
        }

        with open("models/metadata.yaml", "w") as f:
            yaml.dump(metadata, f)

        feature_schema = {
            "features": [
                "phobert_embedding[768]",
                "text_length",
                "text_word_count"
            ]
        }

        with open("models/feature_schema.json", "w") as f:
            json.dump(feature_schema, f, indent=2)

        print("Training completed successfully")

if __name__ == "__main__":
    main()