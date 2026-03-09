# notebooks/infer-model-vihallu.py
"""
infer-model-vihallu.py
Run inference on train split, save predictions + log to MLflow.
Mirrors feature engineering from train-model-vihallu.py exactly.
"""

import os
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
import mlflow
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity


EMB_PATH            = "features/phobert_embeddings.npy"
VISTRAL_PATH        = "data/vihallu-vistral-dataset/vistral_train_predictions_with_probs.csv"
DATA_PATH           = "data/vihallu-dataset/vihallu-train.csv"
MODEL_DIR           = Path("models/lgbm")
FEATURE_SCHEMA_PATH = "models/feature_schema.json"
OUT_PATH            = "predictions/vihallu_infer_predictions.csv"

LABELS = ["extrinsic", "no", "intrinsic"]


def simple_feats(c: str, p: str, r: str) -> list:
    """6-dim: [char_len, word_count] for context / prompt / response."""
    feats = []
    for t in [c, p, r]:
        t = str(t)
        feats.extend([len(t), len(t.split())])
    return feats


def build_cosine_sim(X_embed: np.ndarray) -> np.ndarray:
    centroid = X_embed.mean(axis=0, keepdims=True)   # (1, 768)
    return cosine_similarity(X_embed, centroid)       # (N, 1)


def resolve_id_column(df: pd.DataFrame, fallback_df: pd.DataFrame) -> np.ndarray:
    if "id" in df.columns:
        return df["id"].values
    if "id" in fallback_df.columns:
        return fallback_df["id"].values
    return np.arange(len(df))


with open(FEATURE_SCHEMA_PATH) as f:
    feature_schema = json.load(f)

EXPECTED_DIM = feature_schema["feature_dim"]
print(f"[INFO] Expected feature dim: {EXPECTED_DIM}")

df         = pd.read_csv(DATA_PATH).fillna("")
embeddings = np.load(EMB_PATH)
vistral_df = pd.read_csv(VISTRAL_PATH)

assert len(df) == len(embeddings), (
    f"DataFrame rows ({len(df)}) != embeddings ({len(embeddings)})"
)
assert len(df) == len(vistral_df), (
    f"DataFrame rows ({len(df)}) != vistral rows ({len(vistral_df)})"
)

X_embed = embeddings                                         # (N, 768)

X_simple = np.array([
    simple_feats(c, p, r)
    for c, p, r in zip(df["context"], df["prompt"], df["response"])
])                                                           # (N, 6)

X_sim = build_cosine_sim(X_embed)                           # (N, 1)

X_vistral = vistral_df[
    ["prob_no", "prob_extrinsic", "prob_intrinsic"]
].values                                                     # (N, 3)

X = np.hstack([X_embed, X_simple, X_sim, X_vistral])       # (N, 778)

assert X.shape[1] == EXPECTED_DIM, (
    f"Feature dim mismatch: got {X.shape[1]}, expected {EXPECTED_DIM}"
)
print(f"[OK] Feature matrix: {X.shape}")

model_files = sorted(MODEL_DIR.glob("fold_*.txt"))
assert len(model_files) > 0, f"No fold model files found in {MODEL_DIR}"
print(f"[INFO] Loading {len(model_files)} fold models...")

fold_probs = []
for model_path in model_files:
    booster = lgb.Booster(model_file=str(model_path))
    fold_probs.append(booster.predict(X))                   # (N, 3)

probs     = np.mean(fold_probs, axis=0)                     # (N, 3)
pred_idx  = np.argmax(probs, axis=1)
pred_label = [LABELS[i] for i in pred_idx]

id_col = resolve_id_column(df, vistral_df)

out_df = pd.DataFrame({
    "id":              id_col,
    "predict_label":   pred_label,
    "prob_extrinsic":  probs[:, 0],
    "prob_no":         probs[:, 1],
    "prob_intrinsic":  probs[:, 2],
})

Path("predictions").mkdir(parents=True, exist_ok=True)
out_df.to_csv(OUT_PATH, index=False)
print(f"[INFO] Predictions saved to {OUT_PATH}  shape={out_df.shape}")

try:
    mlflow.set_tracking_uri(
        os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    )
    mlflow.set_experiment("vihallu-pipeline")

    with mlflow.start_run(run_name="vihallu-inference"):
        mlflow.log_params({
            "num_models":  len(model_files),
            "feature_dim": X.shape[1],
            "n_samples":   len(df),
        })
        mlflow.log_artifact(OUT_PATH, artifact_path="predictions")
        mlflow.log_artifact(FEATURE_SCHEMA_PATH, artifact_path="schema")
        print("[INFO] MLflow logging done.")
except Exception as e:
    print(f"[WARN] MLflow logging skipped: {e}")

print("[DONE] Inference complete.")