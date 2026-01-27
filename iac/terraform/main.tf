# iac/terraform/main.tf

provider "kubernetes" {
  # config_path = "~/.kube/config" 
}

resource "kubernetes_namespace" "namespaces" {
  for_each = toset([
    "istio-system",
    "knative-serving",
    "kserve",
    "observability",
    "mlflow",
    "hallucination-prod"
  ])
  metadata {
    name = each.key
  }
}