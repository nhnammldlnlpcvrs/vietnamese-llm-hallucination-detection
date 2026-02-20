# sripts/pull_model_from_registry.py
"""
pull_model_from_registry.py
Pull 'production' alias model from MLflow Registry → backend/model_store/
Called by CI/CD (docker/build.sh) before building the serving image.
"""

import os
import shutil
import mlflow
import mlflow.artifacts
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException


MODEL_NAME    = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
MODEL_ALIAS   = os.getenv("MLFLOW_MODEL_ALIAS", "production") 
DOWNLOAD_DIR  = os.getenv("MODEL_STORE_DIR", "backend/model_store")


def main():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    mlflow.set_tracking_uri(tracking_uri)

    print(f"[INFO] MLflow URI  : {tracking_uri}")
    print(f"[INFO] Model name  : {MODEL_NAME}")
    print(f"[INFO] Alias       : {MODEL_ALIAS}")

    client = MlflowClient()

    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    except MlflowException as e:
        raise RuntimeError(
            f"No model '{MODEL_NAME}' with alias '{MODEL_ALIAS}' found.\n"
            f"Run auto_promote_registry.py first.\nMLflow error: {e}"
        )

    version   = mv.version
    run_id    = mv.run_id
    model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"

    print(f"[INFO] Found version: {version}  (run_id: {run_id})")

    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
        print(f"[INFO] Cleaned old model store: {DOWNLOAD_DIR}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print(f"[INFO] Downloading model artifacts to {DOWNLOAD_DIR} ...")
    mlflow.artifacts.download_artifacts(
        artifact_uri=model_uri,
        dst_path=DOWNLOAD_DIR,
    )

    manifest = {
        "model_name":  MODEL_NAME,
        "alias":       MODEL_ALIAS,
        "version":     version,
        "run_id":      run_id,
        "download_dir": DOWNLOAD_DIR,
    }
    manifest_path = os.path.join(DOWNLOAD_DIR, "model_manifest.json")
    import json
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[OK] Model v{version} downloaded to '{DOWNLOAD_DIR}'")
    print(f"[OK] Manifest written: {manifest_path}")


if __name__ == "__main__":
    main()