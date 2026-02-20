# scripts/auto_promote_registry.py
"""
auto_promote_registry.py
Find best MLflow run → register model → set 'production' alias.
"""

import os
import time
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException


EXPERIMENT_NAME  = "vihallu-pipeline"
MODEL_NAME       = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
METRIC_NAME      = "oof_macro_f1"
HIGHER_IS_BETTER = True
MIN_METRIC       = float(os.getenv("MIN_PROMOTE_METRIC", "0.0"))


def get_best_run(client: MlflowClient, experiment_id: str):
    """Return the run with the best oof_macro_f1."""
    order = "DESC" if HIGHER_IS_BETTER else "ASC"
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"metrics.{METRIC_NAME} > {MIN_METRIC}",
        order_by=[f"metrics.{METRIC_NAME} {order}"],
        max_results=1,
    )
    if not runs:
        raise RuntimeError(
            f"No runs found in experiment '{EXPERIMENT_NAME}' "
            f"with {METRIC_NAME} > {MIN_METRIC}"
        )
    return runs[0]


def ensure_model_exists(client: MlflowClient, model_name: str) -> None:
    """Create registered model if it doesn't exist yet."""
    try:
        client.get_registered_model(model_name)
    except MlflowException:
        client.create_registered_model(
            name=model_name,
            description="Vietnamese LLM Hallucination Detector (PhoBERT + LightGBM)",
        )
        print(f"[INFO] Created registered model '{model_name}'")


def promote_to_production(client: MlflowClient, model_name: str, run) -> str:
    """
    Register run as new model version and set 'production' alias.
    Previous 'production' alias is moved to 'production-previous' for rollback.
    Returns new version string.
    """
    run_id       = run.info.run_id
    metric_value = run.data.metrics[METRIC_NAME]

    print(f"[INFO] Best run_id : {run_id}")
    print(f"[INFO] {METRIC_NAME}: {metric_value:.4f}")

    model_uri = f"runs:/{run_id}/model"

    # Register new version
    print(f"[INFO] Registering model '{model_name}' from run {run_id}...")
    result  = mlflow.register_model(model_uri=model_uri, name=model_name)
    version = result.version

    # Wait until model version is READY
    print(f"[INFO] Waiting for version {version} to be ready...")
    for _ in range(30):
        mv = client.get_model_version(name=model_name, version=version)
        if mv.status == "READY":
            break
        time.sleep(2)
    else:
        raise RuntimeError(f"Model version {version} never reached READY state")

    try:
        current = client.get_model_version_by_alias(model_name, "production")
        client.set_registered_model_alias(
            name=model_name,
            alias="production-previous",
            version=current.version,
        )
        print(f"[INFO] Previous production (v{current.version}) → 'production-previous'")
    except MlflowException:
        pass  # No previous production alias — first deploy

    # Set new version as 'production'
    client.set_registered_model_alias(
        name=model_name,
        alias="production",
        version=version,
    )

    # Tag the version with promotion metadata
    client.set_model_version_tag(
        name=model_name,
        version=version,
        key="promoted_by",
        value="auto_promote_registry.py",
    )
    client.set_model_version_tag(
        name=model_name,
        version=version,
        key=METRIC_NAME,
        value=str(metric_value),
    )

    print(f"[OK] '{model_name}' v{version} → alias 'production'")
    return version


def main():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    print(f"[INFO] MLflow URI  : {tracking_uri}")
    print(f"[INFO] Model name  : {MODEL_NAME}")
    print(f"[INFO] Experiment  : {EXPERIMENT_NAME}")

    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise RuntimeError(f"Experiment '{EXPERIMENT_NAME}' not found")

    ensure_model_exists(client, MODEL_NAME)

    best_run = get_best_run(client, experiment.experiment_id)
    version  = promote_to_production(client, MODEL_NAME, best_run)

    print(f"\n[DONE] Promotion complete → '{MODEL_NAME}' alias 'production' = v{version}")


if __name__ == "__main__":
    main()