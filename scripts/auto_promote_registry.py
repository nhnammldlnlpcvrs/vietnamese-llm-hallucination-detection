# scripts/auto_promote_registry.py
import mlflow
from mlflow.tracking import MlflowClient

EXPERIMENT_NAME = "vihallu-pipeline"
MODEL_NAME = "vihallu-detector"
METRIC_NAME = "oof_macro_f1"
HIGHER_IS_BETTER = True


def get_best_run(client, experiment_id):
    order = "DESC" if HIGHER_IS_BETTER else "ASC"

    runs = client.search_runs(
        experiment_ids=[experiment_id],
        order_by=[f"metrics.{METRIC_NAME} {order}"],
        max_results=1,
    )

    if not runs:
        raise RuntimeError("No runs found in experiment")

    return runs[0]


def promote_to_production(client, model_name, run):
    run_id = run.info.run_id
    metric_value = run.data.metrics[METRIC_NAME]

    print(f"Best run: {run_id}")
    print(f"{METRIC_NAME}: {metric_value}")

    model_uri = f"runs:/{run_id}/model"

    # Register model
    result = mlflow.register_model(
        model_uri=model_uri,
        name=model_name,
    )

    version = result.version
    print(f"📦 Registered {model_name} v{version}")

    # Archive old Production models
    for mv in client.search_model_versions(f"name='{model_name}'"):
        if mv.current_stage == "Production":
            client.transition_model_version_stage(
                name=model_name,
                version=mv.version,
                stage="Archived",
            )

    # Promote new version
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage="Production",
    )

    print("Promoted to Production")


def main():
    mlflow.set_experiment(EXPERIMENT_NAME)
    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise RuntimeError(f"Experiment '{EXPERIMENT_NAME}' not found")

    best_run = get_best_run(client, experiment.experiment_id)
    promote_to_production(client, MODEL_NAME, best_run)


if __name__ == "__main__":
    main()
