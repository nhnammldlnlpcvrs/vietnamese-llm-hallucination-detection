# notebooks/train-model-vihallu.py
import os
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


EXPERIMENT_NAME = "vihallu-pipeline"
NUM_FOLDS = 5
RANDOM_STATE = 42

LABEL_MAP = {
    "extrinsic": 0,
    "no": 1,
    "intrinsic": 2
}

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

mlflow.set_tracking_uri(
    os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
)
mlflow.set_experiment(EXPERIMENT_NAME)


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


class LGBMEnsemble(mlflow.pyfunc.PythonModel):

    def load_context(self, context):
        models_dir = context.artifacts["models_dir"]
        self.models = []

        for fname in sorted(os.listdir(models_dir)):
            if fname.endswith(".txt"):
                self.models.append(
                    lgb.Booster(
                        model_file=os.path.join(models_dir, fname)
                    )
                )

    def predict(self, context, model_input):
        if isinstance(model_input, pd.DataFrame):
            model_input = model_input.values

        preds = [m.predict(model_input) for m in self.models]
        mean_preds = np.mean(preds, axis=0)

        return pd.DataFrame(
            mean_preds,
            columns=[
                "prob_extrinsic",
                "prob_no",
                "prob_intrinsic"
            ]
        )


def main():

    print("Tracking URI:", mlflow.get_tracking_uri())

    contexts, prompts, responses, y = load_dataset()

    X_embed = load_phobert_embeddings()

    X_simple = np.array([
        simple_feats(c, p, r)
        for c, p, r in zip(contexts, prompts, responses)
    ])

    X_sim = np.array([
        cosine_similarity(
            X_embed[i].reshape(1, -1),
            X_embed[i].reshape(1, -1)
        )[0][0]
        for i in range(len(X_embed))
    ]).reshape(-1, 1)

    X_vistral = load_vistral_feats()

    X = np.hstack([
        X_embed,
        X_simple,
        X_sim,
        X_vistral
    ])

    assert X.shape[1] == 778, f"Feature mismatch: {X.shape[1]}"

    with mlflow.start_run(run_name="vihallu-train") as run:

        print("Run ID:", run.info.run_id)

        mlflow.log_params({
            "num_folds": NUM_FOLDS,
            "random_state": RANDOM_STATE,
            "feature_dim": X.shape[1],
            "git_commit": get_git_commit()
        })

        skf = StratifiedKFold(
            n_splits=NUM_FOLDS,
            shuffle=True,
            random_state=RANDOM_STATE
        )

        os.makedirs("models/lgbm", exist_ok=True)
        oof_preds = np.zeros((len(y), 3))

        for fold, (tr, va) in enumerate(skf.split(X, y)):

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

            mlflow.log_metric(f"fold_{fold}_macro_f1", fold_f1)

            clf.booster_.save_model(
                f"models/lgbm/fold_{fold}.txt"
            )

        oof_f1 = f1_score(
            y,
            np.argmax(oof_preds, axis=1),
            average="macro"
        )

        mlflow.log_metric("oof_macro_f1", oof_f1)

        print("OOF F1:", oof_f1)

        print("Logging model to MLflow...")

        sample_output = pd.DataFrame(
            np.zeros((5, 3)),
            columns=[
                "prob_extrinsic",
                "prob_no",
                "prob_intrinsic"
            ]
        )

        signature = infer_signature(
            pd.DataFrame(X[:5]),
            sample_output
        )

        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=LGBMEnsemble(),
            artifacts={"models_dir": "models/lgbm"},
            signature=signature,
            input_example=pd.DataFrame(X[:5]),
            pip_requirements=[
                "lightgbm",
                "mlflow",
                "numpy",
                "pandas",
                "scikit-learn"
            ]
        )

        print("Model logged successfully.")

        metadata = {
            "label_map": LABEL_MAP,
            "feature_dim": X.shape[1],
            "oof_macro_f1": float(oof_f1)
        }

        os.makedirs("models", exist_ok=True)

        with open("models/metadata.yaml", "w") as f:
            yaml.dump(metadata, f)

        mlflow.log_artifact("models/metadata.yaml")

        print("Training completed successfully")


if __name__ == "__main__":
    main()