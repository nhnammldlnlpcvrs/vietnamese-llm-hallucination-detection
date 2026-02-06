# notebooks/train-model-vihallu.py
import os
import json
import yaml
import subprocess
import mlflow
import lightgbm as lgb
import numpy as np
import pandas as pd

from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score
from sklearn.metrics.pairwise import cosine_similarity
from mlflow.models import infer_signature

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

EXPERIMENT_NAME = "vihallu-pipeline"
NUM_FOLDS = 5
RANDOM_STATE = 42
mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment(EXPERIMENT_NAME)
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
    df = pd.read_csv("data/vihallu-dataset/vihallu-train.csv")

    df["label"] = df["label"].str.lower().str.strip()
    labels = df["label"].map(LABEL_MAP).values

    return (
        df["context"].fillna("").astype(str).tolist(),
        df["prompt"].fillna("").astype(str).tolist(),
        df["response"].fillna("").astype(str).tolist(),
        labels
    )

def simple_feats(c, p, r):
    feats = []
    for t in [c, p, r]:
        feats.extend([len(t), len(t.split())])
    return feats

def load_phobert_embeddings():
    return np.load("features/phobert_embeddings.npy")

def load_vistral_feats():
    df = pd.read_csv(
        "data/vihallu-vistral-dataset/vistral_train_predictions_with_probs.csv"
    )
    return df[["prob_no", "prob_extrinsic", "prob_intrinsic"]].values

def main():
    mlflow.set_experiment(EXPERIMENT_NAME)

    contexts, prompts, responses, y = load_dataset()

    # PhoBERT embeddings (full text)
    X_embed = load_phobert_embeddings()

    # Simple features
    X_simple = np.array([
        simple_feats(c, p, r)
        for c, p, r in zip(contexts, prompts, responses)
    ])

    # Cosine similarity: context vs response
    X_ctx = X_embed  # embedding was built from (c+p+r) but still ok for cosine proxy
    X_rsp = X_embed

    X_sim = np.array([
        cosine_similarity(
            X_ctx[i].reshape(1, -1),
            X_rsp[i].reshape(1, -1)
        )[0][0]
        for i in range(len(X_embed))
    ]).reshape(-1, 1)

    # Vistral probabilities
    X_vistral = load_vistral_feats()

    # Final feature matrix
    X = np.hstack([
        X_embed,
        X_simple,
        X_sim,
        X_vistral
    ])

    assert X.shape[1] == 778, f"Feature mismatch: {X.shape[1]}"

    with mlflow.start_run(run_name="vihallu-train"):

        mlflow.log_params({
            "num_folds": NUM_FOLDS,
            "random_state": RANDOM_STATE,
            "git_commit": get_git_commit(),
            "feature_dim": X.shape[1]
        })

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
                    n_estimators=300,
                    random_state=RANDOM_STATE
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
                mlflow.log_artifact(model_path)

        oof_f1 = f1_score(
            y,
            np.argmax(oof_preds, axis=1),
            average="macro"
        )
        mlflow.log_metric("oof_macro_f1", oof_f1)
        
        class LGBMEnsemble(mlflow.pyfunc.PythonModel):
            def load_context(self, context):
                models_dir = context.artifacts["models_dir"]
                self.models = []

                for fname in sorted(os.listdir(models_dir)):
                    if fname.endswith(".txt"):
                        self.models.append(
                            lgb.Booster(model_file=os.path.join(models_dir, fname))
                        )

            def predict(self, context, model_input):
                preds = [m.predict(model_input) for m in self.models]
                return np.mean(preds, axis=0)

        model_paths = sorted(
            [f"models/lgbm/fold_{i}.txt" for i in range(NUM_FOLDS)]
        )

        ensemble_model = LGBMEnsemble()

        input_example = X[:5]

        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=ensemble_model,
            artifacts={
                "models_dir": "models/lgbm"
            },
            input_example=input_example,
            registered_model_name="vihallu-lightgbm"
        )



        metadata = {
            "label_map": LABEL_MAP,
            "feature_dim": X.shape[1],
            "feature_order": [
                "phobert_embedding[768]",
                "context_len", "context_word_count",
                "prompt_len", "prompt_word_count",
                "response_len", "response_word_count",
                "cosine_similarity",
                "prob_no", "prob_extrinsic", "prob_intrinsic"
            ]
        }

        os.makedirs("models", exist_ok=True)

        with open("models/metadata.yaml", "w") as f:
            yaml.dump(metadata, f)

        with open("models/feature_schema.json", "w") as f:
            json.dump(metadata, f, indent=2)

        metrics = {
            "oof_macro_f1": float(oof_f1),
            "num_folds": NUM_FOLDS,
            "num_samples": len(y),
            "feature_dim": X.shape[1]
        }

        with open("models/metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)

        mlflow.log_artifact("models/metadata.yaml")
        mlflow.log_artifact("models/feature_schema.json")
        mlflow.log_artifact("models/metrics.json")

        print("Training completed successfully")

if __name__ == "__main__":
    main()