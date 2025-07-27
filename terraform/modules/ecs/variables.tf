# ECS Module Variables

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for ECS tasks"
  type        = list(string)
}

variable "target_group_arn" {
  description = "ALB target group ARN"
  type        = string
}

variable "secrets_arn" {
  description = "AWS Secrets Manager secret ARN"
  type        = string
}

variable "container_image" {
  description = "Docker image for the application"
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 5000
}

variable "cpu" {
  description = "CPU units for ECS task"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory for ECS task in MB"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum number of ECS tasks for auto scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks for auto scaling"
  type        = number
  default     = 10
}

variable "environment_variables" {
  description = "Environment variables for the container"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
