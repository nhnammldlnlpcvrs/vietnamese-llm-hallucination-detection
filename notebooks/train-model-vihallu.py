# notebooks/train-model-vihallu.py
"""
train-model-vihallu.py
Train PhoBERT + LightGBM ensemble for Vietnamese hallucination detection.
Outputs: models/lgbm/, models/metadata.yaml, models/feature_schema.json
"""

import os
import json
import yaml
import subprocess

import mlflow
import mlflow.pyfunc
import lightgbm as lgb
import numpy as np
import pandas as pd

from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score
from sklearn.metrics.pairwise import cosine_similarity
from mlflow.models import infer_signature


EXPERIMENT_NAME = "vihallu-pipeline"
MODEL_NAME      = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
NUM_FOLDS       = 5
RANDOM_STATE    = 42

LABEL_MAP = {
    "extrinsic":  0,
    "no":         1,
    "intrinsic":  2,
}

FEAT_DIMS = {
    "phobert_embeddings": 768,
    "simple_features":    6,    # len + word_count for context / prompt / response
    "cosine_similarity":  1,    # embedding vs corpus center
    "vistral_probs":      3,    # prob_no, prob_extrinsic, prob_intrinsic
}
EXPECTED_DIM = sum(FEAT_DIMS.values())  # 778

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

# NOTE: mlflow.set_tracking_uri / set_experiment intentionally moved inside
# main() so that importing this module doesn't crash when MLflow is offline.


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"]
        ).decode().strip()
    except Exception:
        return "unknown"


def load_dataset():
    df = pd.read_csv("data/vihallu-dataset/vihallu-train.csv")
    df["label"] = df["label"].str.lower().str.strip()
    labels = df["label"].map(LABEL_MAP).values

    return (
        df["context"].fillna("").astype(str).tolist(),
        df["prompt"].fillna("").astype(str).tolist(),
        df["response"].fillna("").astype(str).tolist(),
        labels,
        df,
    )


def simple_feats(c: str, p: str, r: str) -> list:
    """6-dim: [char_len, word_count] for each of context / prompt / response."""
    feats = []
    for t in [c, p, r]:
        t = str(t)
        feats.extend([len(t), len(t.split())])
    return feats


def build_cosine_sim(X_embed: np.ndarray) -> np.ndarray:
    """
    (N, 1) — cosine similarity of each sample embedding vs corpus centroid.
    Fix: previously compared embedding[i] with itself → always 1.0 (useless).
    Now measures how 'central' a sample is relative to the whole corpus.
    """
    centroid = X_embed.mean(axis=0, keepdims=True)          # (1, 768)
    sim = cosine_similarity(X_embed, centroid)               # (N, 1)
    return sim


def load_phobert_embeddings() -> np.ndarray:
    return np.load("features/phobert_embeddings.npy")


def load_vistral_feats() -> np.ndarray:
    df = pd.read_csv(
        "data/vihallu-vistral-dataset/vistral_train_predictions_with_probs.csv"
    )
    # Keep column order consistent with FEAT_DIMS declaration
    return df[["prob_no", "prob_extrinsic", "prob_intrinsic"]].values


def build_feature_matrix(
    contexts, prompts, responses, X_embed, X_vistral
) -> np.ndarray:
    X_simple = np.array([
        simple_feats(c, p, r)
        for c, p, r in zip(contexts, prompts, responses)
    ])                                                       # (N, 6)

    X_sim = build_cosine_sim(X_embed)                       # (N, 1)

    X = np.hstack([X_embed, X_simple, X_sim, X_vistral])   # (N, 778)
    assert X.shape[1] == EXPECTED_DIM, (
        f"Feature dim mismatch: got {X.shape[1]}, expected {EXPECTED_DIM}"
    )
    return X


class LGBMEnsemble(mlflow.pyfunc.PythonModel):
    """
    Loads all fold models from artifact directory and averages predictions.
    Input:  pd.DataFrame of shape (N, 778)
    Output: pd.DataFrame with columns [prob_extrinsic, prob_no, prob_intrinsic]
    """

    def load_context(self, context):
        models_dir = context.artifacts["models_dir"]
        self.models = []
        for fname in sorted(os.listdir(models_dir)):
            if fname.endswith(".txt"):
                self.models.append(
                    lgb.Booster(model_file=os.path.join(models_dir, fname))
                )
        if not self.models:
            raise RuntimeError(f"No .txt model files found in {models_dir}")

    def predict(self, context, model_input):
        if isinstance(model_input, pd.DataFrame):
            model_input = model_input.values

        preds = np.mean([m.predict(model_input) for m in self.models], axis=0)

        return pd.DataFrame(
            preds,
            columns=["prob_extrinsic", "prob_no", "prob_intrinsic"],
        )


def main():
    mlflow.set_tracking_uri(
        os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    )
    mlflow.set_experiment(EXPERIMENT_NAME)

    print(f"[INFO] MLflow Tracking URI: {mlflow.get_tracking_uri()}")
    print(f"[INFO] Model registry name: {MODEL_NAME}")

    contexts, prompts, responses, y, _ = load_dataset()

    X_embed   = load_phobert_embeddings()
    X_vistral = load_vistral_feats()

    X = build_feature_matrix(contexts, prompts, responses, X_embed, X_vistral)
    print(f"[INFO] Feature matrix shape: {X.shape}")

    os.makedirs("models", exist_ok=True)
    feature_schema = {
        "feature_dim":  int(X.shape[1]),
        "components":   FEAT_DIMS,
        "label_map":    LABEL_MAP,
        "column_order": ["phobert_embeddings", "simple_features",
                         "cosine_similarity", "vistral_probs"],
    }
    with open("models/feature_schema.json", "w") as f:
        json.dump(feature_schema, f, indent=2)
    print("[INFO] feature_schema.json saved.")

    with mlflow.start_run(run_name="vihallu-train") as run:
        print(f"[INFO] Run ID: {run.info.run_id}")

        mlflow.log_params({
            "num_folds":    NUM_FOLDS,
            "random_state": RANDOM_STATE,
            "feature_dim":  X.shape[1],
            "git_commit":   get_git_commit(),
            "model_name":   MODEL_NAME,
        })

        os.makedirs("models/lgbm", exist_ok=True)
        oof_preds = np.zeros((len(y), 3))

        skf = StratifiedKFold(
            n_splits=NUM_FOLDS,
            shuffle=True,
            random_state=RANDOM_STATE,
        )

        for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
            clf = lgb.LGBMClassifier(
                objective="multiclass",
                num_class=3,
                num_leaves=64,
                learning_rate=0.05,
                n_estimators=300,
                random_state=RANDOM_STATE,
                n_jobs=2,
            )
            clf.fit(X[tr_idx], y[tr_idx])

            fold_preds          = clf.predict_proba(X[va_idx])
            oof_preds[va_idx]   = fold_preds

            fold_f1 = f1_score(
                y[va_idx],
                np.argmax(fold_preds, axis=1),
                average="macro",
            )
            mlflow.log_metric(f"fold_{fold}_macro_f1", fold_f1)
            print(f"  Fold {fold}: macro F1 = {fold_f1:.4f}")

            model_path = f"models/lgbm/fold_{fold}.txt"
            clf.booster_.save_model(model_path)

        oof_f1 = f1_score(y, np.argmax(oof_preds, axis=1), average="macro")
        mlflow.log_metric("oof_macro_f1", oof_f1)
        print(f"[INFO] OOF macro F1: {oof_f1:.4f}")

        sample_input  = pd.DataFrame(X[:5])
        sample_output = pd.DataFrame(
            np.zeros((5, 3)),
            columns=["prob_extrinsic", "prob_no", "prob_intrinsic"],
        )
        signature = infer_signature(sample_input, sample_output)

        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=LGBMEnsemble(),
            artifacts={"models_dir": "models/lgbm"},
            signature=signature,
            input_example=sample_input,
            pip_requirements=[
                "lightgbm",
                "mlflow==2.11.3",
                "numpy",
                "pandas",
                "scikit-learn",
            ],
        )
        print("[INFO] Model logged to MLflow.")

        metadata = {
            "label_map":    LABEL_MAP,
            "feature_dim":  int(X.shape[1]),
            "oof_macro_f1": float(oof_f1),
            "model_name":   MODEL_NAME,
        }
        with open("models/metadata.yaml", "w") as f:
            yaml.dump(metadata, f)

        mlflow.log_artifact("models/metadata.yaml")
        mlflow.log_artifact("models/feature_schema.json")

        print("[INFO] Training completed successfully.")


if __name__ == "__main__":
    main()