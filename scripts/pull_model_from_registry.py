# sripts/pull_model_from_registry.py
import os
import shutil
import mlflow
from mlflow.tracking import MlflowClient

MODEL_NAME = "vihallu-detector"
STAGE = "Production"

DOWNLOAD_DIR = "backend/model_store"


def main():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    client = MlflowClient()

    print(f"Fetching model {MODEL_NAME} ({STAGE})")

    versions = client.get_latest_versions(MODEL_NAME, stages=[STAGE])
    if not versions:
        raise RuntimeError("No model in Production stage")

    model_uri = f"models:/{MODEL_NAME}/{STAGE}"

    # Clean old model
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print("Downloading model artifact...")

    mlflow.artifacts.download_artifacts(
        artifact_uri=model_uri,
        dst_path=DOWNLOAD_DIR,
    )

    print("Model downloaded to backend/model_store")


if __name__ == "__main__":
    main()