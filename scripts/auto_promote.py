# scripts/auto_promote.py
"""
auto_promote.py
Lightweight promote helper — wraps auto_promote_registry with env-var gates.
Can be called from CI/CD after training to conditionally promote.
Usage: python scripts/auto_promote.py --min-f1 0.75
"""

import argparse
import os
import sys

import mlflow
from mlflow.tracking import MlflowClient


EXPERIMENT_NAME  = "vihallu-pipeline"
MODEL_NAME       = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
METRIC_NAME      = "oof_macro_f1"


def parse_args():
    parser = argparse.ArgumentParser(description="Auto-promote best MLflow model run.")
    parser.add_argument(
        "--min-f1",
        type=float,
        default=float(os.getenv("MIN_PROMOTE_METRIC", "0.0")),
        help="Minimum oof_macro_f1 required for promotion (default: 0.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be promoted without actually doing it.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        print(f"[ERROR] Experiment '{EXPERIMENT_NAME}' not found.", file=sys.stderr)
        sys.exit(1)

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=[f"metrics.{METRIC_NAME} DESC"],
        max_results=1,
    )

    if not runs:
        print("[ERROR] No runs found.", file=sys.stderr)
        sys.exit(1)

    best_run = runs[0]
    metric   = best_run.data.metrics.get(METRIC_NAME, 0.0)

    print(f"[INFO] Best run   : {best_run.info.run_id}")
    print(f"[INFO] {METRIC_NAME}: {metric:.4f}  (threshold: {args.min_f1})")

    if metric < args.min_f1:
        print(
            f"[SKIP] {metric:.4f} < min threshold {args.min_f1}. "
            "Model not promoted."
        )
        sys.exit(0)

    if args.dry_run:
        print("[DRY RUN] Would promote — exiting without changes.")
        sys.exit(0)

    # Delegate to full promotion logic
    from scripts.auto_promote_registry import ensure_model_exists, promote_to_production
    ensure_model_exists(client, MODEL_NAME)
    version = promote_to_production(client, MODEL_NAME, best_run)
    print(f"[DONE] Promoted '{MODEL_NAME}' v{version} → alias 'production'")


if __name__ == "__main__":
    main()