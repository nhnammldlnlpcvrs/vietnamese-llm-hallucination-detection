import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri("sqlite:///mlflow.db")

EXPERIMENT_NAME = "vihallu-pipeline"
METRIC_NAME = "oof_macro_f1"
THRESHOLD = 0.75
PROD_TAG = "Production"

def main():
    client = MlflowClient()

    exp = client.get_experiment_by_name(EXPERIMENT_NAME)
    if exp is None:
        print("Experiment not found")
        return

    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        order_by=[f"metrics.{METRIC_NAME} DESC"],
        max_results=1,
    )

    if not runs:
        print("No runs found")
        return

    best_run = runs[0]
    best_f1 = best_run.data.metrics.get(METRIC_NAME)

    print(f"Best run: {best_run.info.run_id}")
    print(f"{METRIC_NAME}: {best_f1:.4f}")

    if best_f1 < THRESHOLD:
        print("Below threshold → not promoted")
        return

    client.set_tag(best_run.info.run_id, "stage", PROD_TAG)
    print("Promoted to Production")

if __name__ == "__main__":
    main()