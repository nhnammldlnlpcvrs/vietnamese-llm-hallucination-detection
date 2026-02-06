# notebooks/infer-model-vihallu.py
import os
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
import mlflow

from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

EMB_PATH = "features/phobert_embeddings.npy"
VISTRAL_PATH = "data/vihallu-vistral-dataset/vistral_train_predictions_with_probs.csv"
DATA_PATH = "data/vihallu-dataset/vihallu-train.csv"

MODEL_DIR = Path("models/lgbm")
FEATURE_SCHEMA_PATH = "models/feature_schema.json"
OUT_PATH = "predictions/vihallu_infer_predictions.csv"

LABELS = ["extrinsic", "no", "intrinsic"]

def simple_feats(c, p, r):
    feats = []
    for t in [c, p, r]:
        t = str(t)
        feats.extend([len(t), len(t.split())])
    return feats


with open(FEATURE_SCHEMA_PATH) as f:
    feature_schema = json.load(f)

EXPECTED_DIM = feature_schema["feature_dim"]

df = pd.read_csv(DATA_PATH)
df.fillna("", inplace=True)

embeddings = np.load(EMB_PATH)
vistral_df = pd.read_csv(VISTRAL_PATH)

assert len(df) == len(embeddings) == len(vistral_df), "Data length mismatch"

X_embed = embeddings  # (N, 768)

X_simple = np.array([
    simple_feats(c, p, r)
    for c, p, r in zip(
        df["context"],
        df["prompt"],
        df["response"]
    )
])

X_sim = np.array([
    cosine_similarity(
        X_embed[i].reshape(1, -1),
        X_embed[i].reshape(1, -1)
    )[0][0]
    for i in range(len(X_embed))
]).reshape(-1, 1)

X_vistral = vistral_df[
    ["prob_no", "prob_extrinsic", "prob_intrinsic"]
].values

X = np.hstack([
    X_embed,
    X_simple,
    X_sim,
    X_vistral
])

assert X.shape[1] == EXPECTED_DIM, (
    f"Feature dim mismatch: got {X.shape[1]}, expected {EXPECTED_DIM}"
)

print(f"[OK] Feature dim = {X.shape[1]}")

probs = []

model_files = sorted(MODEL_DIR.glob("fold_*.txt"))
assert len(model_files) > 0, "No model files found"

for model_path in model_files:
    model = lgb.Booster(model_file=str(model_path))
    probs.append(model.predict(X))

probs = np.mean(probs, axis=0)

pred_idx = np.argmax(probs, axis=1)
pred_label = [LABELS[i] for i in pred_idx]

out_df = pd.DataFrame({
    "id": df.get("id", vistral_df.get("id")),
    "predict_label": pred_label,
    "prob_extrinsic": probs[:, 0],
    "prob_no": probs[:, 1],
    "prob_intrinsic": probs[:, 2],
})

Path("predictions").mkdir(exist_ok=True)
out_df.to_csv(OUT_PATH, index=False)

try:
    with mlflow.start_run(run_name="vihallu-inference"):
        mlflow.log_param("num_models", len(model_files))
        mlflow.log_param("feature_dim", X.shape[1])
        mlflow.log_artifact(OUT_PATH, artifact_path="predictions")
except Exception as e:
    print(f"[WARN] MLflow logging skipped: {e}")

print(f"DONE! Inference saved to {OUT_PATH}")