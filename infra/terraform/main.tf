# AI-f Sovereign OS - Cloud Infrastructure Baseline (AWS)

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = "ai_f_user"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

provider "aws" {
  region = var.region
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  
  tags = {
    Name = "ai-f-vpc"
    Project = "LEVI-AI"
  }
}

resource "aws_db_instance" "postgres" {
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "15.5"
  instance_class       = "db.t3.medium"
  db_name              = "face_recognition"
  username             = var.db_user
  password             = var.db_password
  skip_final_snapshot  = true
  storage_encrypted    = true # HIPAA/SOC2 requirement
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "ai-f-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}

resource "aws_eks_cluster" "backend" {
  name     = "ai-f-cluster"
  role_arn = aws_iam_role.eks_role.arn

  vpc_config {
    subnet_ids = aws_subnet.private[*].id
  }
}
