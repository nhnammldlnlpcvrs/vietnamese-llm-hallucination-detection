# docker/build.sh
#!/bin/sh
# mlops/mlflow/entrypoint.sh

set -e

DB_URI="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/${DB_NAME:-mlflow}"

if [ -n "$MLFLOW_S3_BUCKET" ]; then
    ARTIFACT_ROOT="s3://${MLFLOW_S3_BUCKET}/artifacts"
    echo "[INFO] Using S3 artifact root: $ARTIFACT_ROOT"
elif [ -n "$MLFLOW_GCS_BUCKET" ]; then
    ARTIFACT_ROOT="gs://${MLFLOW_GCS_BUCKET}/artifacts"
    echo "[INFO] Using GCS artifact root: $ARTIFACT_ROOT"
else
    ARTIFACT_ROOT="/mlflow/artifacts"
    echo "[WARN] No cloud bucket set — using local path: $ARTIFACT_ROOT"
    echo "[WARN] Ensure a PersistentVolume is mounted at /mlflow/artifacts"
fi

exec mlflow server \
    --backend-store-uri  "$DB_URI" \
    --default-artifact-root "$ARTIFACT_ROOT" \
    --host 0.0.0.0 \
    --port 5000 \
    --workers "${MLFLOW_WORKERS:-2}"