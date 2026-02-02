# notebooks/train-model-vihallu.py
import os
import json
import yaml
import mlflow
import mlflow.pytorch
import lightgbm as lgb
import numpy as np
import torch

from transformers import (
    AutoTokenizer,
    AutoModel,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score

EXPERIMENT_NAME = "vihallu-pipeline"
PHOBERT_MODEL = "vinai/phobert-base"
NLI_MODEL = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
NER_MODEL = "undertheseanlp/vietnamese-ner-v1.4.0a2"
VISTRAL_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

NUM_FOLDS = 5
DEVICE = "cpu"

def load_dataset():
    """
    RETURN:
        contexts: List[str]
        prompts:  List[str]
        responses: List[str]
        labels: np.array shape (N,) with values {0,1,2}
    """
    raise NotImplementedError("Load your hallucination dataset here")

def simple_feats(context, prompt, response):
    feats = []
    for t in [context, prompt, response]:
        s = t or ""
        feats.extend([len(s), len(s.split())])
    return feats

def extract_embeddings(texts, tokenizer, model):
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        out = model(**inputs)
        emb = out.last_hidden_state.mean(dim=1)
    return emb.cpu().numpy()

def main():
    mlflow.set_experiment(EXPERIMENT_NAME)

    contexts, prompts, responses, labels = load_dataset()

    tokenizer = AutoTokenizer.from_pretrained(PHOBERT_MODEL)
    model = AutoModel.from_pretrained(PHOBERT_MODEL).to(DEVICE).eval()

    with mlflow.start_run(run_name="vihallu-full-pipeline"):

        mlflow.log_params({
            "phobert_model": PHOBERT_MODEL,
            "nli_model": NLI_MODEL,
            "ner_model": NER_MODEL,
            "vistral_model": VISTRAL_MODEL,
            "num_folds": NUM_FOLDS
        })

        X_embed = extract_embeddings(
            [f"{c} {p} {r}" for c, p, r in zip(contexts, prompts, responses)],
            tokenizer,
            model
        )

        X_simple = np.array([
            simple_feats(c, p, r)
            for c, p, r in zip(contexts, prompts, responses)
        ])

        X = np.hstack([X_embed, X_simple])
        y = labels

        skf = StratifiedKFold(n_splits=NUM_FOLDS, shuffle=True, random_state=42)
        oof_preds = np.zeros((len(y), 3))

        os.makedirs("lgbm_models", exist_ok=True)

        for fold, (tr, va) in enumerate(skf.split(X, y)):
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

            model_path = f"lgbm_models/fold_{fold}.txt"
            clf.booster_.save_model(model_path)
            mlflow.log_artifact(model_path, artifact_path="models/lgbm")

        f1 = f1_score(y, np.argmax(oof_preds, axis=1), average="macro")
        mlflow.log_metric("lgbm_oof_macro_f1", f1)

        mlflow.pytorch.log_model(model, artifact_path="models/phobert")
        tokenizer.save_pretrained("phobert_tokenizer")
        mlflow.log_artifacts("phobert_tokenizer", artifact_path="models/phobert_tokenizer")

        metadata = {
            "nli_model": NLI_MODEL,
            "ner_model": NER_MODEL,
            "vistral_model": VISTRAL_MODEL,
            "label_map": {
                "0": "Extrinsic",
                "1": "No",
                "2": "Intrinsic"
            }
        }

        with open("metadata.yaml", "w") as f:
            yaml.dump(metadata, f)

        mlflow.log_artifact("metadata.yaml", artifact_path="models")

        feature_schema = {
            "features": [
                "phobert_embedding[768]",
                "context_len",
                "context_words",
                "prompt_len",
                "prompt_words",
                "response_len",
                "response_words"
            ]
        }

        with open("feature_schema.json", "w") as f:
            json.dump(feature_schema, f, indent=2)

        mlflow.log_artifact("feature_schema.json")

        mlflow.log_artifact(
            "backend/model/inference_model.py",
            artifact_path="inference"
        )

        print("Training & MLflow logging completed")

if __name__ == "__main__":
    main()