# CalStack Terraform Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "calstack"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

variable "certificate_arn" {
  description = "ARN of the SSL certificate from AWS Certificate Manager"
  type        = string
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Container Configuration
variable "container_image" {
  description = "Docker image for the application"
  type        = string
  default     = "calstack:latest"
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 5000
}

# ECS Configuration
variable "ecs_cpu" {
  description = "CPU units for ECS task (256, 512, 1024, etc.)"
  type        = number
  default     = 256
}

variable "ecs_memory" {
  description = "Memory for ECS task in MB"
  type        = number
  default     = 512
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_min_capacity" {
  description = "Minimum number of ECS tasks for auto scaling"
  type        = number
  default     = 1
}

variable "ecs_max_capacity" {
  description = "Maximum number of ECS tasks for auto scaling"
  type        = number
  default     = 10
}

# Secrets (sensitive variables)
variable "flask_secret_key" {
  description = "Flask secret key"
  type        = string
  sensitive   = true
}

variable "mongo_uri" {
  description = "MongoDB Atlas connection string"
  type        = string
  sensitive   = true
}

variable "sendgrid_api_key" {
  description = "SendGrid API key"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret (from client_secret.json)"
  type        = string
  sensitive   = true
}

variable "ms_client_id" {
  description = "Microsoft OAuth client ID"
  type        = string
  sensitive   = true
}

variable "ms_client_secret" {
  description = "Microsoft OAuth client secret"
  type        = string
  sensitive   = true
}

variable "azure_application_id" {
  description = "Azure application ID"
  type        = string
  sensitive   = true
}

variable "azure_directory_id" {
  description = "Azure directory/tenant ID"
  type        = string
  sensitive   = true
}

# Optional features
variable "enable_cloudfront" {
  description = "Enable CloudFront CDN"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "CalStack"
    Environment = "prod"
    ManagedBy   = "Terraform"
  }
}
