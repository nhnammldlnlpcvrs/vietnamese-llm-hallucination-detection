"""
scripts/pull_model_from_registry.py
Pull model from MLflow Registry (via S3/MinIO) → backend/model_store/
"""
import json
import os
import shutil
import sys
import boto3
from botocore.exceptions import ClientError

MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
MODEL_ALIAS = os.getenv("MLFLOW_MODEL_ALIAS", "production")
DOWNLOAD_DIR = os.getenv("MODEL_STORE_DIR", "backend/model_store")
S3_ENDPOINT = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://localhost:9000")
S3_BUCKET = os.getenv("MLFLOW_S3_BUCKET", "vihallu-mlflow")
S3_PREFIX = f"{S3_BUCKET}/artifacts"

def download_from_s3() -> None:
    
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        verify=os.getenv("MLFLOW_S3_IGNORE_TLS", "false").lower() == "true"
    )
    
    print(f"[INFO] Downloading from S3:")
    print(f"  Endpoint: {S3_ENDPOINT}")
    print(f"  Bucket:   {S3_BUCKET}")
    print(f"  Prefix:   {S3_PREFIX}")
    
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
        print(f"[INFO] Cleaned old model store: {DOWNLOAD_DIR}")
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix="artifacts/"
        )
        
        if "Contents" not in response:
            print(f"[WARN] No objects found in {S3_PREFIX}")
            return
        
        for obj in response["Contents"]:
            key = obj["Key"]
            local_file = os.path.join(DOWNLOAD_DIR, key.replace("artifacts/", ""))
            
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            
            s3_client.download_file(S3_BUCKET, key, local_file)
            print(f"  ✓ Downloaded: {key}")
        
        print(f"[OK] Model downloaded to '{DOWNLOAD_DIR}'")
        
        manifest = {
            "model_name": MODEL_NAME,
            "alias": MODEL_ALIAS,
            "source": "s3",
            "bucket": S3_BUCKET,
        }
        manifest_path = os.path.join(DOWNLOAD_DIR, "model_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"[OK] Manifest: {manifest_path}")
        
    except ClientError as e:
        print(f"[ERROR] S3 download failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_from_s3()