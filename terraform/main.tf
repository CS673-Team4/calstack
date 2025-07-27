# CalStack AWS Infrastructure
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC and Networking
module "networking" {
  source = "./modules/networking"
  
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  
  availability_zones = data.aws_availability_zones.available.names
  
  tags = var.tags
}

# Secrets Manager for environment variables
module "secrets" {
  source = "./modules/secrets"
  
  project_name = var.project_name
  environment  = var.environment
  
  secrets = {
    flask_secret_key     = var.flask_secret_key
    mongo_uri           = var.mongo_uri
    sendgrid_api_key    = var.sendgrid_api_key
    google_client_secret = var.google_client_secret
    ms_client_id        = var.ms_client_id
    ms_client_secret    = var.ms_client_secret
    azure_application_id = var.azure_application_id
    azure_directory_id  = var.azure_directory_id
  }
  
  tags = var.tags
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  project_name = var.project_name
  environment  = var.environment
  
  vpc_id              = module.networking.vpc_id
  public_subnet_ids   = module.networking.public_subnet_ids
  certificate_arn     = var.certificate_arn
  domain_name         = var.domain_name
  
  tags = var.tags
}

# ECS Cluster and Service
module "ecs" {
  source = "./modules/ecs"
  
  project_name = var.project_name
  environment  = var.environment
  
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  security_group_ids = [module.networking.ecs_security_group_id]
  
  target_group_arn = module.alb.target_group_arn
  secrets_arn      = module.secrets.secret_arn
  
  # Container configuration
  container_image    = var.container_image
  container_port     = var.container_port
  cpu               = var.ecs_cpu
  memory            = var.ecs_memory
  desired_count     = var.ecs_desired_count
  min_capacity      = var.ecs_min_capacity
  max_capacity      = var.ecs_max_capacity
  
  # Environment variables (non-sensitive)
  environment_variables = {
    FLASK_DEBUG              = "0"
    OAUTH2_REDIRECT_URI      = "https://${var.domain_name}/oauth2callback"
    MS_OUTLOOK_REDIRECT_URI  = "https://${var.domain_name}/oauth2callback/outlook"
    DOMAIN                   = var.domain_name
  }
  
  tags = var.tags
}

# Route 53 and CloudFront (optional)
module "dns" {
  source = "./modules/dns"
  count  = var.enable_cloudfront ? 1 : 0
  
  project_name = var.project_name
  environment  = var.environment
  
  domain_name     = var.domain_name
  alb_dns_name    = module.alb.dns_name
  alb_zone_id     = module.alb.zone_id
  certificate_arn = var.certificate_arn
  
  tags = var.tags
}
