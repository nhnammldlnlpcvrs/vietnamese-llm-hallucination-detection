#!/bin/sh
set -e

DB_URI="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/${DB_NAME:-mlflow}"

if [ -n "$MLFLOW_S3_BUCKET" ]; then
    ARTIFACT_ROOT="s3://${MLFLOW_S3_BUCKET}/artifacts"
elif [ -n "$MLFLOW_GCS_BUCKET" ]; then
    ARTIFACT_ROOT="gs://${MLFLOW_GCS_BUCKET}/artifacts"
else
    ARTIFACT_ROOT="/mlflow/artifacts"
fi

echo "[INFO] Artifact root: $ARTIFACT_ROOT"

exec mlflow server \
    --backend-store-uri  "$DB_URI" \
    --default-artifact-root "$ARTIFACT_ROOT" \
    --host 0.0.0.0 \
    --port 5000 \
    --workers "${MLFLOW_WORKERS:-2}"