# iac/terraform/main.tf

variable "kube_config" {
  type    = string
  default = ""
}

provider "kubernetes" {
  config_path = var.kube_config != "" ? var.kube_config : null
}

provider "helm" {
  kubernetes {
    config_path = var.kube_config != "" ? var.kube_config : null
  }
}