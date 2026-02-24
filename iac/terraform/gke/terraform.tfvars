# iac/terraform/gke/terraform.tfvars
# Điền các giá trị thực tế trước khi chạy terraform apply

project_id       = "your-gcp-project-id"   # GCP Project ID
region           = "asia-southeast1"
zone             = "asia-southeast1-a"
cluster_name     = "vihallu-cluster"
node_count       = 2
machine_type     = "e2-standard-4"

ghcr_username    = "nhnammldlnlpcvrs"
ghcr_token       = ""   # GitHub PAT với write:packages

minio_access_key = "minio"
minio_secret_key = "minio123"
