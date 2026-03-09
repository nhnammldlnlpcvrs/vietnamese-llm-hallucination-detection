"""
observability/evidently/drift_service.py
Evidently data drift service with:
  - Prometheus metrics export (/metrics endpoint)
  - Scheduled drift checks (configurable interval)
  - FastAPI HTTP server for health + manual trigger
  - Supports prediction drift (label distribution shift)
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from prometheus_client import (
    Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
)
from fastapi.responses import Response
import uvicorn

from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently.metrics import (
    DatasetDriftMetric,
    DataDriftTable,
    ColumnDriftMetric,
)


REFERENCE_DATA_PATH = os.getenv(
    "REFERENCE_DATA_PATH",
    "predictions/vihallu_infer_predictions.csv"   # training predictions as reference
)
CURRENT_DATA_PATH = os.getenv(
    "CURRENT_DATA_PATH",
    "predictions/current_predictions.csv"          # live predictions
)
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports/drift")
CHECK_INTERVAL_SEC = int(os.getenv("DRIFT_CHECK_INTERVAL_SEC", "300"))  # 5 min
PORT = int(os.getenv("EVIDENTLY_PORT", "8001"))

FEATURE_COLUMNS = ["prob_extrinsic", "prob_no", "prob_intrinsic"]
LABEL_COLUMN    = "predict_label"
LABELS          = ["extrinsic", "no", "intrinsic"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


dataset_drift_detected = Gauge(
    "evidently_dataset_drift_detected",
    "1 if dataset drift detected, 0 otherwise"
)
drifted_features_count = Gauge(
    "evidently_drifted_features_count",
    "Number of features with detected drift"
)
share_of_drifted_features = Gauge(
    "evidently_share_of_drifted_features",
    "Share of drifted features (0-1)"
)
feature_drift_score = Gauge(
    "evidently_feature_drift_score",
    "Drift score per feature",
    ["feature"]
)
current_label_ratio = Gauge(
    "evidently_current_label_ratio",
    "Current prediction label distribution",
    ["label"]
)
reference_label_ratio = Gauge(
    "evidently_reference_label_ratio",
    "Reference prediction label distribution",
    ["label"]
)
drift_checks_total = Counter(
    "evidently_drift_checks_total",
    "Total number of drift checks run"
)
drift_check_errors_total = Counter(
    "evidently_drift_check_errors_total",
    "Total number of drift check errors"
)
last_check_timestamp = Gauge(
    "evidently_last_check_timestamp_seconds",
    "Unix timestamp of last drift check"
)


def load_data(path: str, label: str) -> Optional[pd.DataFrame]:
    """Load CSV data, return None if not available."""
    try:
        df = pd.read_csv(path)
        logger.info(f"Loaded {label} data: {df.shape} from {path}")
        return df
    except FileNotFoundError:
        logger.warning(f"{label} data not found at {path}")
        return None
    except Exception as e:
        logger.error(f"Failed to load {label} data: {e}")
        return None


def update_label_metrics(ref_df: pd.DataFrame, cur_df: pd.DataFrame) -> None:
    """Update Prometheus label distribution metrics."""
    for label in LABELS:
        ref_ratio = (ref_df[LABEL_COLUMN] == label).mean() if LABEL_COLUMN in ref_df.columns else 0.0
        cur_ratio = (cur_df[LABEL_COLUMN] == label).mean() if LABEL_COLUMN in cur_df.columns else 0.0
        reference_label_ratio.labels(label=label).set(ref_ratio)
        current_label_ratio.labels(label=label).set(cur_ratio)


def run_drift_check() -> dict:
    """
    Run Evidently drift check, update Prometheus metrics, save HTML report.
    Returns summary dict.
    """
    drift_checks_total.inc()

    ref_df = load_data(REFERENCE_DATA_PATH, "reference")
    cur_df = load_data(CURRENT_DATA_PATH, "current")

    if ref_df is None or cur_df is None:
        drift_check_errors_total.inc()
        raise RuntimeError("Reference or current data not available")

    # Use probability columns for drift detection
    cols = [c for c in FEATURE_COLUMNS if c in ref_df.columns and c in cur_df.columns]
    if not cols:
        drift_check_errors_total.inc()
        raise RuntimeError(f"Feature columns {FEATURE_COLUMNS} not found in data")

    # Build Evidently report
    report = Report(metrics=[
        DatasetDriftMetric(),
        DataDriftTable(),
        *[ColumnDriftMetric(column_name=col) for col in cols],
    ])
    report.run(
        reference_data=ref_df[cols],
        current_data=cur_df[cols],
    )

    result = report.as_dict()
    metrics = result.get("metrics", [])

    # Parse DatasetDriftMetric
    summary = {}
    for m in metrics:
        if m.get("metric") == "DatasetDriftMetric":
            r = m.get("result", {})
            summary["drift_detected"]          = int(r.get("dataset_drift", False))
            summary["drifted_features"]        = r.get("number_of_drifted_columns", 0)
            summary["share_drifted_features"]  = r.get("share_of_drifted_columns", 0.0)

            dataset_drift_detected.set(summary["drift_detected"])
            drifted_features_count.set(summary["drifted_features"])
            share_of_drifted_features.set(summary["share_drifted_features"])

        elif m.get("metric") == "ColumnDriftMetric":
            col  = m.get("result", {}).get("column_name", "unknown")
            score = m.get("result", {}).get("drift_score", 0.0)
            feature_drift_score.labels(feature=col).set(score)

    update_label_metrics(ref_df, cur_df)
    last_check_timestamp.set(time.time())

    # Save HTML report
    Path(REPORT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    report_path = f"{REPORT_OUTPUT_DIR}/drift_report_latest.html"
    report.save_html(report_path)
    logger.info(f"Drift report saved to {report_path} | summary={summary}")

    return summary


def run_scheduler():
    """Background thread: run drift check every CHECK_INTERVAL_SEC."""
    logger.info(f"Drift scheduler started (interval={CHECK_INTERVAL_SEC}s)")
    while True:
        try:
            summary = run_drift_check()
            logger.info(f"Scheduled drift check done: {summary}")
        except Exception as e:
            logger.error(f"Scheduled drift check failed: {e}")
        time.sleep(CHECK_INTERVAL_SEC)


app = FastAPI(title="Evidently Drift Service", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "evidently-drift"}


@app.get("/metrics")
def metrics():
    """Prometheus scrape endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/drift/check")
def trigger_drift_check():
    """Manual drift check trigger."""
    try:
        summary = run_drift_check()
        return {"status": "ok", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/drift/report")
def get_report_path():
    """Return path to latest HTML report."""
    report_path = f"{REPORT_OUTPUT_DIR}/drift_report_latest.html"
    if Path(report_path).exists():
        return {"report_path": report_path, "exists": True}
    return {"report_path": report_path, "exists": False}


if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    try:
        run_drift_check()
    except Exception as e:
        logger.warning(f"Initial drift check skipped: {e}")

    uvicorn.run(app, host="0.0.0.0", port=PORT)