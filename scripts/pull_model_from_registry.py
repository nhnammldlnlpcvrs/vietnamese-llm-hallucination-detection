"""
scripts/pull_model_from_registry.py
Pull 'production' alias model from MLflow Registry → backend/model_store/
Called by CI before building the serving Docker image.

Usage:
    python scripts/pull_model_from_registry.py

Env vars:
    MLFLOW_TRACKING_URI     MLflow server URL
    MLFLOW_S3_ENDPOINT_URL  MinIO/S3 endpoint
    AWS_ACCESS_KEY_ID       S3 credentials
    AWS_SECRET_ACCESS_KEY   S3 credentials
    MLFLOW_MODEL_NAME       Model name in registry (default: vihallu-detector)
    MLFLOW_MODEL_ALIAS      Alias to pull (default: production)
    MODEL_STORE_DIR         Local destination (default: backend/model_store)
    SKIP_MLFLOW_PULL        Skip download if set to '1' (default: 0)
"""
import json
import os
import shutil
import sys
import mlflow
import mlflow.artifacts
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
MODEL_ALIAS = os.getenv("MLFLOW_MODEL_ALIAS", "production")
DOWNLOAD_DIR = os.getenv("MODEL_STORE_DIR", "backend/model_store")
SKIP_PULL = os.getenv("SKIP_MLFLOW_PULL", "0") == "1"

def model_exists_and_valid(path: str) -> bool:
    manifest_path = os.path.join(path, "model_manifest.json")
    return os.path.exists(path) and os.path.exists(manifest_path)

def main() -> None:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    
    print(f"[INFO] MLflow URI : {tracking_uri}")
    print(f"[INFO] Model name : {MODEL_NAME}")
    print(f"[INFO] Alias : {MODEL_ALIAS}")
    print(f"[INFO] Destination: {DOWNLOAD_DIR}")
    
    if model_exists_and_valid(DOWNLOAD_DIR):
        print(f"[OK] Model already exists at '{DOWNLOAD_DIR}', skipping download")
        return
    
    if SKIP_PULL:
        print(f"[WARN] SKIP_MLFLOW_PULL=1, creating empty model_store")
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        return
    
    client = MlflowClient()
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    except MlflowException as e:
        print(f"[ERROR] MLflow error: {e}")
        print(f"[WARN] Cannot connect to MLflow server at {tracking_uri}")
        
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        print(f"[WARN] Created empty model_store at {DOWNLOAD_DIR}")
        print(f"[HINT] Run this locally: export MLFLOW_TRACKING_URI=<your-mlflow-url>")
        print(f"[HINT] Then: python scripts/pull_model_from_registry.py")
        return
    except Exception as e:
        print(f"[ERROR] Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)
    
    version = mv.version
    run_id = mv.run_id
    model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
    
    print(f"[INFO] Found version : {version}")
    print(f"[INFO] Run ID : {run_id}")
    
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
        print(f"[INFO] Cleaned old model store: {DOWNLOAD_DIR}")
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    print(f"[INFO] Downloading model artifacts ...")
    try:
        mlflow.artifacts.download_artifacts(
            artifact_uri=model_uri,
            dst_path=DOWNLOAD_DIR,
        )
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        sys.exit(1)
    
    files = list(os.walk(DOWNLOAD_DIR))
    total_files = sum(len(f) for _, _, f in files)
    print(f"[INFO] Downloaded {total_files} files")
    
    manifest = {
        "model_name": MODEL_NAME,
        "alias": MODEL_ALIAS,
        "version": version,
        "run_id": run_id,
        "download_dir": DOWNLOAD_DIR,
    }
    manifest_path = os.path.join(DOWNLOAD_DIR, "model_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"[OK] Model v{version} downloaded to '{DOWNLOAD_DIR}'")
    print(f"[OK] Manifest: {manifest_path}")

if __name__ == "__main__":
    main()