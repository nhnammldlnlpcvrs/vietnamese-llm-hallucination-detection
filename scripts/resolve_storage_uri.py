"""
scripts/resolve_storage_uri.py
Resolve the correct S3 storageUri for the production model from MLflow Registry.
Called by CI/CD before 'kubectl apply' or 'helmfile sync'.

Usage:
    python scripts/resolve_storage_uri.py
    # Outputs: s3://vihallu-mlflow/artifacts/1/<run_id>/artifacts/model
    
    # Or update inference-service.yaml directly:
    python scripts/resolve_storage_uri.py --update-yaml mlops/kserve/inference-service.yaml
"""

import os
import re
import sys
import argparse
import mlflow
from mlflow.tracking import MlflowClient


MODEL_NAME  = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
MODEL_ALIAS = os.getenv("MLFLOW_MODEL_ALIAS", "production")


def get_storage_uri() -> str:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    mv = client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    run_id = mv.run_id

    run = client.get_run(run_id)
    artifact_uri = run.info.artifact_uri  # e.g. s3://vihallu-mlflow/artifacts/1/<run_id>/artifacts

    storage_uri = f"{artifact_uri}/model"

    print(f"[INFO] Model     : {MODEL_NAME}@{MODEL_ALIAS}")
    print(f"[INFO] Version   : {mv.version}")
    print(f"[INFO] Run ID    : {run_id}")
    print(f"[INFO] StorageUri: {storage_uri}")

    return storage_uri


def update_yaml(yaml_path: str, storage_uri: str) -> None:
    with open(yaml_path) as f:
        content = f.read()

    updated = re.sub(
        r'(storageUri:\s*")[^"]*(")',
        rf'\g<1>{storage_uri}\g<2>',
        content,
    )
    updated = re.sub(
        r'(storageUri:\s*)s3://[^\s\n]+',
        rf'\g<1>{storage_uri}',
        updated,
    )

    with open(yaml_path, "w") as f:
        f.write(updated)

    print(f"[OK] Updated {yaml_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-yaml", help="Path to YAML file to update storageUri in")
    args = parser.parse_args()

    storage_uri = get_storage_uri()

    if args.update_yaml:
        update_yaml(args.update_yaml, storage_uri)
    else:
        print(storage_uri)


if __name__ == "__main__":
    main()