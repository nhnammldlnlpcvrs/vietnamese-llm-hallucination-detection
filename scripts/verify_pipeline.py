# scripts/verify_pipeline.py
"""
scripts/verify_pipeline.py
Smoke-test the full MLflow + DVC pipeline without running full training.
Run this before 'dvc repro' on a new environment to catch config issues early.

Usage:
    python scripts/verify_pipeline.py
    python scripts/verify_pipeline.py --full   # also checks model artifact download
"""

import argparse
import json
import os
import sys
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException


CHECKS_PASSED = []
CHECKS_FAILED = []

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"


def ok(name: str, msg: str = ""):
    CHECKS_PASSED.append(name)
    print(f"  {GREEN}✓{RESET} {name}" + (f"  — {msg}" if msg else ""))


def fail(name: str, msg: str = ""):
    CHECKS_FAILED.append(name)
    print(f"  {RED}✗{RESET} {name}" + (f"  — {msg}" if msg else ""))


def warn(name: str, msg: str = ""):
    print(f"  {YELLOW}⚠{RESET} {name}" + (f"  — {msg}" if msg else ""))


def check_env_vars():
    print("\n[1] Environment variables")
    required = ["MLFLOW_TRACKING_URI"]
    for var in required:
        val = os.getenv(var)
        if val:
            ok(var, val)
        else:
            fail(var, "not set")

    optional = ["MLFLOW_MODEL_NAME", "MLFLOW_MODEL_ALIAS", "MLFLOW_S3_BUCKET"]
    for var in optional:
        val = os.getenv(var)
        if val:
            ok(var, val)
        else:
            warn(var, f"not set — will use default")


def check_local_files():
    print("\n[2] Local file structure")
    required_files = [
        "dvc.yaml",
        "dvc.lock",
        "notebooks/embed_phobert.py",
        "notebooks/train-model-vihallu.py",
        "notebooks/infer-model-vihallu.py",
        "scripts/auto_promote_registry.py",
        "scripts/pull_model_from_registry.py",
        "backend/model/mlflow_loader.py",
        "data/vihallu-dataset/vihallu-train.csv",
        "data/vihallu-vistral-dataset/vistral_train_predictions_with_probs.csv",
    ]

    for path in required_files:
        if Path(path).exists():
            ok(path)
        else:
            fail(path, "missing")

    optional_files = [
        "features/phobert_embeddings.npy",
        "models/feature_schema.json",
        "models/metadata.yaml",
        "models/lgbm/fold_0.txt",
    ]
    print("  Optional (produced by DVC stages):")
    for path in optional_files:
        if Path(path).exists():
            ok(f"  {path}")
        else:
            warn(f"  {path}", "not yet produced — run 'dvc repro'")


def check_feature_schema():
    print("\n[3] Feature schema consistency")
    schema_path = "models/feature_schema.json"
    if not Path(schema_path).exists():
        warn("feature_schema.json", "not found — run 'dvc repro' stage train first")
        return

    with open(schema_path) as f:
        schema = json.load(f)

    expected_dim = 778
    got_dim = schema.get("feature_dim", 0)
    if got_dim == expected_dim:
        ok("feature_dim", f"{got_dim}")
    else:
        fail("feature_dim", f"got {got_dim}, expected {expected_dim}")

    required_components = ["phobert_embeddings", "simple_features", "cosine_similarity", "vistral_probs"]
    components = schema.get("components", {})
    for comp in required_components:
        if comp in components:
            ok(f"component.{comp}", str(components[comp]))
        else:
            fail(f"component.{comp}", "missing from schema")


def check_mlflow_connection():
    print("\n[4] MLflow connectivity")
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    try:
        experiments = client.search_experiments()
        ok("MLflow reachable", f"{len(experiments)} experiments found")
    except Exception as e:
        fail("MLflow reachable", str(e))
        return

    exp_name = "vihallu-pipeline"
    experiment = client.get_experiment_by_name(exp_name)
    if experiment:
        ok("experiment exists", exp_name)
    else:
        warn("experiment exists", f"'{exp_name}' not found — will be created on first run")


def check_model_registry(full: bool = False):
    print("\n[5] MLflow Model Registry")
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    model_name = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
    model_alias = os.getenv("MLFLOW_MODEL_ALIAS", "production")

    try:
        client.get_registered_model(model_name)
        ok("registered model exists", model_name)
    except MlflowException:
        warn("registered model", f"'{model_name}' not registered yet — run auto_promote_registry.py")
        return

    try:
        mv = client.get_model_version_by_alias(model_name, model_alias)
        ok(f"alias '{model_alias}'", f"→ v{mv.version}  run_id={mv.run_id[:8]}...")
    except MlflowException:
        fail(f"alias '{model_alias}'", f"not set — run auto_promote_registry.py")
        return

    if full:
        print(f"  Attempting model download (--full mode)...")
        try:
            import tempfile, shutil
            model_uri = f"models:/{model_name}@{model_alias}"
            tmp = tempfile.mkdtemp()
            mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=tmp)
            shutil.rmtree(tmp)
            ok("model download", f"artifact download successful")
        except Exception as e:
            fail("model download", str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Also test model artifact download")
    args = parser.parse_args()

    print("=" * 55)
    print("  MLflow + DVC Pipeline Verification")
    print("=" * 55)

    check_env_vars()
    check_local_files()
    check_feature_schema()
    check_mlflow_connection()
    check_model_registry(full=args.full)

    print("\n" + "=" * 55)
    print(f"  {GREEN}PASSED{RESET}: {len(CHECKS_PASSED)}   {RED}FAILED{RESET}: {len(CHECKS_FAILED)}")
    print("=" * 55)

    if CHECKS_FAILED:
        print(f"\n{RED}Pipeline verification FAILED. Fix issues above before 'dvc repro'.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}All checks passed. Safe to run 'dvc repro'.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()