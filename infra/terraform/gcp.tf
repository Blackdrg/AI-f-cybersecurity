# GCP Multi-cloud Infrastructure for AI-f
# Google Cloud Platform deployment supporting sovereign cloud requirements

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "ai-f-network"
  auto_create_subnetworks = false
  
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_subnetwork" "private" {
  name          = "ai-f-private"
  ip_cidr_range = "10.10.0.0/16"
  region        = var.region
  network       = google_compute_network.main.id
  private_ip_google_access = true
}

# Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "postgres" {
  name             = "ai-f-postgres"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier              = "db-custom-2-4096"
    activation_policy = "ALWAYS"
    disk_encryption_configuration {
      enabled = true
    }
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }
    backup_configuration {
      enabled    = true
      start_time = "02:00"
      point_in_time_recovery_enabled = true
    }
  }
  
  deletion_protection = true
}

# Memorystore (Redis)
resource "google_redis_instance" "cache" {
  name           = "ai-f-redis"
  tier           = "STANDARD"
  memory_size_gb = 1
  region         = var.region
  
  redis_configs = {
    maxmemory_policy = "allkeys-lru"
  }
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = "ai-f-gke"
  location = var.region
  
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.main.name
  subnetwork = google_compute_subnetwork.private.name
  
  ip_allocation_policy {
    cluster_ipv4_cidr_block  = "10.20.0.0/14"
    services_ipv4_cidr_block = "10.24.0.0/20"
  }
  
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "APISERVER"]
  }
  
  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"
}

# Node Pool
resource "google_container_node_pool" "primary_nodes" {
  name       = "ai-f-node-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = 2
  
  node_config {
    machine_type = "e2-standard-2"
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    labels = {
      env = "production"
    }
    tags = ["ai-f", "production"]
    
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }
  
  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }
}

# Cloud Storage for model weights and audit logs
resource "google_storage_bucket" "models" {
  name     = "${var.project_id}-ai-f-models"
  location = var.region
  
  encryption {
    default_kms_key_name = google_kms_crypto_key.models.id
  }
  
  versioning {
    enabled = true
  }
}

# KMS for encryption
resource "google_kms_key_ring" "ai_f" {
  name     = "ai-f-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "models" {
  name            = "ai-f-models-key"
  key_ring        = google_kms_key_ring.ai_f.id
  rotation_period = "2592000s"
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "ai_f" {
  provider = google-beta
  location = var.region
  repository_id = "ai-f-images"
  format        = "DOCKER"
  description   = "AI-f container images"
  
  kms_key_name = google_kms_crypto_key.models.id
}

# Output values
output "kubernetes_cluster_name" {
  value = google_container_cluster.primary.name
}

output "kubernetes_cluster_host" {
  value = google_container_cluster.primary.endpoint
}

output "database_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "redis_host" {
  value = google_redis_instance.cache.host
}