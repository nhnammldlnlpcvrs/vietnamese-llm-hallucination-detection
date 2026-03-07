# iac/terraform/gke/main.tf
# GKE Cluster for Vietnamese LLM Hallucination Detection
# Region: asia-southeast1 (Singapore)
# Node: e2-standard-4 (4 CPU, 16GB)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }

  # Remote state trên GCS (uncomment khi dùng thật)
  # backend "gcs" {
  #   bucket = "vihallu-terraform-state"
  #   prefix = "gke/prod"
  # }
}

variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type    = string
  default = "asia-southeast1"
}

variable "zone" {
  type    = string
  default = "asia-southeast1-a"
}

variable "cluster_name" {
  type    = string
  default = "vihallu-cluster"
}

variable "node_count" {
  type    = number
  default = 2
  description = "Number of nodes in default node pool"
}

variable "machine_type" {
  type    = string
  default = "e2-standard-4"   # 4 CPU, 16GB
}

variable "ghcr_username" {
  type      = string
  sensitive = true
}

variable "ghcr_token" {
  type      = string
  sensitive = true
}

variable "minio_access_key" {
  type      = string
  default   = "minio"
  sensitive = true
}

variable "minio_secret_key" {
  type      = string
  default   = "minio123"
  sensitive = true
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

resource "google_compute_network" "vihallu_vpc" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "vihallu_subnet" {
  name          = "${var.cluster_name}-subnet"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.vihallu_vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

resource "google_container_cluster" "vihallu" {
  name     = var.cluster_name
  location = var.zone

  network    = google_compute_network.vihallu_vpc.name
  subnetwork = google_compute_subnetwork.vihallu_subnet.name

  # Remove default node pool — use custom pool below
  remove_default_node_pool = true
  initial_node_count       = 1

  # Networking
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Workload Identity (recommended for GKE)
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Enable HTTP load balancing (for Ingress)
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
  }

  # Maintenance window — off-peak Vietnam time
  maintenance_policy {
    recurring_window {
      start_time = "2024-01-01T20:00:00Z"  # 3AM ICT
      end_time   = "2024-01-02T00:00:00Z"  # 6AM ICT
      recurrence = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA,SU"
    }
  }
}

resource "google_container_node_pool" "vihallu_nodes" {
  name       = "${var.cluster_name}-node-pool"
  location   = var.zone
  cluster    = google_container_cluster.vihallu.name
  node_count = var.node_count

  # Autoscaling
  autoscaling {
    min_node_count = 1
    max_node_count = 4
  }

  # Auto repair + upgrade
  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.machine_type
    disk_size_gb = 50
    disk_type    = "pd-ssd"

    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = {
      env     = "production"
      project = "vihallu"
    }

    tags = ["vihallu-node"]
  }
}

data "google_client_config" "default" {}

provider "kubernetes" {
  host                   = "https://${google_container_cluster.vihallu.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(
    google_container_cluster.vihallu.master_auth[0].cluster_ca_certificate
  )
}

resource "kubernetes_namespace" "hallucination_prod" {
  metadata {
    name = "hallucination-prod"
    labels = {
      env = "production"
    }
  }
  depends_on = [google_container_node_pool.vihallu_nodes]
}

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
  }
  depends_on = [google_container_node_pool.vihallu_nodes]
}

resource "kubernetes_secret" "ghcr" {
  metadata {
    name      = "ghcr-secret"
    namespace = kubernetes_namespace.hallucination_prod.metadata[0].name
  }

  type = "kubernetes.io/dockerconfigjson"

  data = {
    ".dockerconfigjson" = jsonencode({
      auths = {
        "ghcr.io" = {
          username = var.ghcr_username
          password = var.ghcr_token
          auth     = base64encode("${var.ghcr_username}:${var.ghcr_token}")
        }
      }
    })
  }
}

resource "kubernetes_secret" "mlflow" {
  metadata {
    name      = "mlflow-secret"
    namespace = kubernetes_namespace.hallucination_prod.metadata[0].name
  }

  type = "Opaque"

  data = {
    MLFLOW_TRACKING_URI   = "http://mlflow.hallucination-prod.svc.cluster.local:5000"
    MLFLOW_S3_ENDPOINT_URL = "http://minio.hallucination-prod.svc.cluster.local:9000"
  }
}

resource "kubernetes_secret" "aws" {
  metadata {
    name      = "aws-credentials"
    namespace = kubernetes_namespace.hallucination_prod.metadata[0].name
  }

  type = "Opaque"

  data = {
    AWS_ACCESS_KEY_ID     = var.minio_access_key
    AWS_SECRET_ACCESS_KEY = var.minio_secret_key
    AWS_DEFAULT_REGION    = "ap-southeast-1"
  }
}

output "cluster_name" {
  value = google_container_cluster.vihallu.name
}

output "cluster_endpoint" {
  value     = google_container_cluster.vihallu.endpoint
  sensitive = true
}

output "cluster_region" {
  value = var.region
}

output "get_credentials_command" {
  value = "gcloud container clusters get-credentials ${var.cluster_name} --zone ${var.zone} --project ${var.project_id}"
}
