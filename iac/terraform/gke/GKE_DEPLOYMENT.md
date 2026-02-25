# GKE Deployment Guide — Vietnamese LLM Hallucination Detection

This guide explains how to deploy the **Vietnamese LLM Hallucination Detection** system on **Google Kubernetes Engine (GKE)** using **Terraform**, **Ansible**, and **KServe**.

---

## Prerequisites

Make sure the following tools are installed on your machine:

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
gcloud init

# Install GKE authentication plugin and kubectl
gcloud components install gke-gcloud-auth-plugin kubectl

# Verify installations
gcloud --version
kubectl version --client
terraform --version
```

## Step 1 — Create a GCP Project
```bash
# Create project
gcloud projects create vihallu-prod --name="ViHallu Production"

# Set active project
gcloud config set project vihallu-prod

# Enable required APIs
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com \
  artifactregistry.googleapis.com
```

## Step 2 — Create a Terraform Service Account
```bash
# Create service account
gcloud iam service-accounts create terraform-sa \
  --display-name="Terraform Service Account"

# Grant required roles
gcloud projects add-iam-policy-binding vihallu-prod \
  --member="serviceAccount:terraform-sa@vihallu-prod.iam.gserviceaccount.com" \
  --role="roles/container.admin"

gcloud projects add-iam-policy-binding vihallu-prod \
  --member="serviceAccount:terraform-sa@vihallu-prod.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud projects add-iam-policy-binding vihallu-prod \
  --member="serviceAccount:terraform-sa@vihallu-prod.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Download service account key
gcloud iam service-accounts keys create ~/gcp-terraform-key.json \
  --iam-account=terraform-sa@vihallu-prod.iam.gserviceaccount.com

# Export credentials for Terraform
export GOOGLE_APPLICATION_CREDENTIALS=~/gcp-terraform-key.json
```

## Step 3 — Provision GKE with Terraform
```bash
cd iac/terraform/gke

# Edit variables
# - project_id
# - ghcr_token
nano terraform.tfvars

# Initialize and apply Terraform
terraform init
terraform plan
terraform apply
```

### Configure kubectl
```bash
gcloud container clusters get-credentials vihallu-cluster \
  --zone asia-southeast1-a \
  --project vihallu-prod

# Verify cluster access
kubectl get nodes
```

## Step 4 — Deploy KServe and Observability Stack
```bash
cd iac/ansible

# Run Ansible playbook
ansible-playbook setup_gke_stack.yaml -v

# Monitor deployment
watch kubectl get pods -A
```

**Note: On GKE, there is no need to increase the inotify limit for Promtail because GCE VMs already use higher limits by default.**

## Step 5 — Verify InferenceService
```bash
# Check InferenceService status
kubectl get inferenceservice -n hallucination-prod
```

### Get KServe Endpoint
```bash
KSERVE_ENDPOINT=$(kubectl get inferenceservice hallucination-detector \
  -n hallucination-prod \
  -o jsonpath='{.status.url}')

echo "KServe endpoint: $KSERVE_ENDPOINT"
```

### Test Inference
```bash
curl -X POST "$KSERVE_ENDPOINT/v2/models/hallucination-detector/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {
        "name": "context",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["Việt Nam là quốc gia ở Đông Nam Á"]
      },
      {
        "name": "prompt",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["Thủ đô của Việt Nam là gì?"]
      },
      {
        "name": "response",
        "shape": [1],
        "datatype": "BYTES",
        "data": ["Thủ đô của Việt Nam là Tokyo"]
      }
    ]
  }'
```
Expected response:
```bash
{
  "outputs": [
    {"name": "label", "data": ["extrinsic"]},
    {"name": "confidence", "data": [0.87]}
  ]
}
```

## Step 6 — Expose Services (Optional)

For local access via port-forwarding:
```bash
# Grafana
kubectl port-forward svc/grafana 3000:80 -n monitoring &

# Jaeger
kubectl port-forward svc/jaeger 16686:16686 -n monitoring &

# Backend API
kubectl port-forward svc/hallucination-backend 8000:8000 -n hallucination-prod &
```

## Cost Estimate (asia-southeast1)
| Resource          | Spec            | Cost / Month |
| ----------------- | --------------- | ------------ |
| GKE Control Plane | Managed         | $74          |
| 2× e2-standard-4  | 4 CPU / 16 GB   | ~$200        |
| 2× pd-ssd (50 GB) | Persistent Disk | ~$17         |
| **Total**         |                 | **~$291**    |

### Cost Optimization Tips

- Use preemptible nodes (--preemptible)

- Avoid unnecessary features such as:
```bash
--enable-master-authorized-networks
```

### Cleanup
To avoid unexpected billing, destroy all resources when finished:
```bash
terraform destroy
```