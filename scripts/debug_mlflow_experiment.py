import os
import mlflow
from mlflow.tracking import MlflowClient

EXPERIMENT_NAME = "vihallu-pipeline"

def main():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)

    print("Tracking URI:", mlflow.get_tracking_uri())

    client = MlflowClient()

    exp = client.get_experiment_by_name(EXPERIMENT_NAME)

    if exp is None:
        print(f"Experiment '{EXPERIMENT_NAME}' not found.")
        return

    print("Experiment ID:", exp.experiment_id)
    print("Artifact Location:", exp.artifact_location)
    print("Lifecycle Stage:", exp.lifecycle_stage)

    print("\nRecent Runs:")
    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        max_results=5
    )

    for run in runs:
        print("Run ID:", run.info.run_id)
        print("  Status:", run.info.status)
        print("  Artifact URI:", run.info.artifact_uri)
        print("  ---")

if __name__ == "__main__":
    main()