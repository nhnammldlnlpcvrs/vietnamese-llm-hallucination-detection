# GKE Deployment Guide — Vietnamese LLM Hallucination Detection

## Prerequisites

```bash
# Cài gcloud CLI
curl https://sdk.cloud.google.com | bash
gcloud init

# Cài gke-gcloud-auth-plugin (bắt buộc cho kubectl + GKE)
gcloud components install gke-gcloud-auth-plugin

# Verify
gcloud --version
kubectl version --client
terraform --version
```

---

## Bước 1 — Tạo GCP Project

```bash
# Tạo project mới hoặc dùng project có sẵn
gcloud projects create vihallu-prod --name="ViHallu Production"
gcloud config set project vihallu-prod

# Enable APIs cần thiết
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com \
  artifactregistry.googleapis.com
```

---

## Bước 2 — Tạo Service Account cho Terraform

```bash
# Tạo SA
gcloud iam service-accounts create terraform-sa \
  --display-name="Terraform Service Account"

# Grant roles
gcloud projects add-iam-policy-binding vihallu-prod \
  --member="serviceAccount:terraform-sa@vihallu-prod.iam.gserviceaccount.com" \
  --role="roles/container.admin"

gcloud projects add-iam-policy-binding vihallu-prod \
  --member="serviceAccount:terraform-sa@vihallu-prod.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud projects add-iam-policy-binding vihallu-prod \
  --member="serviceAccount:terraform-sa@vihallu-prod.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Download key
gcloud iam service-accounts keys create ~/gcp-terraform-key.json \
  --iam-account=terraform-sa@vihallu-prod.iam.gserviceaccount.com

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=~/gcp-terraform-key.json
```

---

## Bước 3 — Terraform Apply

```bash
cd iac/terraform/gke

# Điền project_id và ghcr_token vào terraform.tfvars
nano terraform.tfvars

# Init + plan + apply
terraform init
terraform plan
terraform apply

# Lấy kubeconfig
gcloud container clusters get-credentials vihallu-cluster \
  --zone asia-southeast1-a \
  --project vihallu-prod

# Verify
kubectl get nodes
```

---

## Bước 4 — Deploy KServe Stack

```bash
cd iac/ansible

# Fix inotify limit (cho Promtail)
# Trên GKE không cần vì nodes là GCE VMs với limit cao hơn

# Chạy playbook
ansible-playbook setup_gke_stack.yaml -v

# Monitor
watch kubectl get pods -A
```

---

## Bước 5 — Verify InferenceService

```bash
# Check status
kubectl get inferenceservice -n hallucination-prod

# Lấy endpoint URL
KSERVE_ENDPOINT=$(kubectl get inferenceservice hallucination-detector \
  -n hallucination-prod \
  -o jsonpath='{.status.url}')

echo "KServe endpoint: $KSERVE_ENDPOINT"

# Test inference
curl -X POST "$KSERVE_ENDPOINT/v2/models/hallucination-detector/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "text",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["Hà Nội là thủ đô của Việt Nam"]
    }]
  }'
```

---

## Bước 6 — Expose Services (Optional)

```bash
# Grafana
kubectl port-forward svc/grafana 3000:80 -n monitoring &

# Jaeger
kubectl port-forward svc/jaeger 16686:16686 -n monitoring &

# Backend
kubectl port-forward svc/hallucination-backend 8000:8000 -n hallucination-prod &
```

---

## Cost Estimate (asia-southeast1)

| Resource | Spec | Cost/month |
|----------|------|-----------|
| GKE Control Plane | - | $74 |
| 2x e2-standard-4 | 4CPU/16GB | ~$200 |
| 2x pd-ssd 50GB | - | ~$17 |
| **Total** | | **~$291/month** |

> Để tiết kiệm: dùng `--no-enable-master-authorized-networks` và preemptible nodes (`--preemptible`)

---

## Cleanup

```bash
# Xóa toàn bộ để tránh billing
terraform destroy
```
