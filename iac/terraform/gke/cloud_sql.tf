# iac/terraform/gke/cloud_sql.tf

resource "google_sql_database_instance" "mlflow_postgres" {
  name                = "mlflow-postgres-${var.project_id}"
  database_version    = "POSTGRES_15"
  region              = var.region
  deletion_protection = false

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    # cloudsql_iam_authentication (not supported for PostgreSQL)
    # database_flags removed completely

    ip_configuration {
      # Use ssl_mode instead of require_ssl
      ssl_mode = "ENCRYPTED_ONLY"
      ipv4_enabled = true
      authorized_networks {
        value = "0.0.0.0/0"
        name  = "allow-all"
      }
    }

    user_labels = {
      env     = "production"
      project = "vihallu"
    }
  }

  depends_on = [google_container_node_pool.vihallu_nodes]
}

# MLflow Database
resource "google_sql_database" "mlflow" {
  name     = "mlflow"
  instance = google_sql_database_instance.mlflow_postgres.name
}

# MLflow Database User
resource "random_password" "mlflow_db_password" {
  length  = 32
  special = true
}

resource "google_sql_user" "mlflow" {
  name     = "mlflow"
  instance = google_sql_database_instance.mlflow_postgres.name
  password = random_password.mlflow_db_password.result
}

# Cloud SQL Auth Proxy Service Account
resource "google_service_account" "cloud_sql_proxy" {
  account_id   = "cloud-sql-proxy-sa"
  display_name = "Cloud SQL Proxy Service Account"
}

resource "google_project_iam_member" "cloud_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_sql_proxy.email}"
}

# Kubernetes Service Account (Workload Identity)
resource "kubernetes_service_account" "cloud_sql_proxy" {
  metadata {
    name      = "cloud-sql-proxy-sa"
    namespace = kubernetes_namespace.hallucination_prod.metadata[0].name
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.cloud_sql_proxy.email
    }
  }
}

# Workload Identity Binding
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.cloud_sql_proxy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[hallucination-prod/cloud-sql-proxy-sa]"
}

# K8s Secret - MLflow DB Credentials
resource "kubernetes_secret" "mlflow_db" {
  metadata {
    name      = "mlflow-db-secret"
    namespace = kubernetes_namespace.hallucination_prod.metadata[0].name
  }

  type = "Opaque"

  data = {
    DB_USER = base64encode("mlflow")
    DB_PASS = base64encode(random_password.mlflow_db_password.result)
    DB_HOST = base64encode("127.0.0.1")
    DB_PORT = base64encode("5432")
    DB_NAME = base64encode("mlflow")
  }

  depends_on = [google_sql_user.mlflow]
}

# Output
output "cloud_sql_instance" {
  value = google_sql_database_instance.mlflow_postgres.connection_name
  description = "Cloud SQL instance connection name (for cloud-sql-proxy)"
}

output "mlflow_db_password" {
  value     = random_password.mlflow_db_password.result
  sensitive = true
}

output "cloud_sql_proxy_sa" {
  value = google_service_account.cloud_sql_proxy.email
}