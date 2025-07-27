# CalStack AWS Production Deployment Strategy

## Architecture Overview

```
Internet → Route 53 → CloudFront → ALB → ECS Fargate → MongoDB Atlas
                                    ↓
                              Auto Scaling Group
                                    ↓
                            Multiple AZ Deployment
```

## Core Components

### 1. **Container Infrastructure**
- **ECS Fargate**: Serverless container hosting
- **Application Load Balancer (ALB)**: SSL termination & load balancing
- **Auto Scaling**: Horizontal scaling based on CPU/memory
- **Multi-AZ**: High availability across availability zones

### 2. **Database**
- **MongoDB Atlas**: Managed MongoDB service
- **No code changes required**: Current `MONGO_URI` works with Atlas
- **Built-in clustering, backups, and monitoring**

### 3. **Networking & Security**
- **VPC**: Isolated network environment
- **Private subnets**: ECS tasks run in private subnets
- **Public subnets**: ALB in public subnets
- **Security Groups**: Granular access control
- **AWS Secrets Manager**: Secure environment variable storage

### 4. **SSL & CDN**
- **AWS Certificate Manager**: Free SSL certificates
- **CloudFront**: Global CDN for static assets
- **Route 53**: DNS management

## Deployment Components

### Infrastructure as Code (Terraform)

```
terraform/
├── main.tf                 # Main infrastructure
├── variables.tf            # Input variables
├── outputs.tf             # Output values
├── modules/
│   ├── networking/        # VPC, subnets, security groups
│   ├── ecs/              # ECS cluster, service, task definition
│   ├── alb/              # Application Load Balancer
│   ├── secrets/          # AWS Secrets Manager
│   └── dns/              # Route 53, CloudFront
└── environments/
    ├── dev/              # Development environment
    ├── staging/          # Staging environment
    └── prod/             # Production environment
```

### Container Setup

```
docker/
├── Dockerfile            # Multi-stage build for production
├── docker-compose.yml    # Local development
├── .dockerignore         # Optimize build context
└── entrypoint.sh         # Container startup script
```

## Implementation Plan

### Phase 1: Containerization
1. **Create production Dockerfile**
2. **Set up Docker Compose for local testing**
3. **Configure environment variable handling**
4. **Test container locally**

### Phase 2: AWS Infrastructure (Terraform)
1. **VPC and networking setup**
2. **ECS cluster and service configuration**
3. **Application Load Balancer with SSL**
4. **Auto Scaling policies**
5. **Secrets Manager for environment variables**

### Phase 3: Database Migration
1. **Set up MongoDB Atlas cluster**
2. **Configure connection string**
3. **Data migration strategy (if needed)**
4. **Test connectivity from ECS**

### Phase 4: CI/CD Pipeline
1. **GitHub Actions workflow**
2. **Docker image building and pushing to ECR**
3. **Automated ECS service updates**
4. **Blue-green deployment strategy**

## Cost Optimization

### Resource Sizing
- **ECS Fargate**: Start with 0.25 vCPU, 512 MB RAM per task
- **Auto Scaling**: 2-10 tasks based on load
- **MongoDB Atlas**: M10 cluster for production (can start with M0 free tier)

### Estimated Monthly Costs
- **ECS Fargate**: ~$15-50 (depending on usage)
- **ALB**: ~$22
- **MongoDB Atlas M10**: ~$57
- **Route 53**: ~$0.50
- **CloudFront**: ~$1-10 (depending on traffic)
- **Total**: ~$95-140/month for production-ready setup

## Benefits of This Architecture

### Scalability
- **Horizontal scaling**: Add more ECS tasks automatically
- **Database scaling**: MongoDB Atlas handles scaling
- **Global distribution**: CloudFront CDN

### Reliability
- **Multi-AZ deployment**: High availability
- **Health checks**: ALB monitors application health
- **Auto recovery**: ECS restarts failed tasks
- **Managed database**: Atlas handles backups and maintenance

### Security
- **Private networking**: Application runs in private subnets
- **SSL everywhere**: End-to-end encryption
- **Secrets management**: No hardcoded credentials
- **Security groups**: Network-level access control

### Operational Excellence
- **Infrastructure as Code**: Reproducible deployments
- **Monitoring**: CloudWatch logs and metrics
- **Automated deployments**: CI/CD pipeline
- **Easy rollbacks**: ECS service updates

## Migration Strategy

### From Current Setup
1. **No code changes needed** for MongoDB Atlas
2. **Environment variables** move to AWS Secrets Manager
3. **OAuth redirect URIs** update to new domain
4. **SendGrid configuration** remains the same
5. **Static files** served via CloudFront

### Zero-Downtime Deployment
1. **Blue-green deployment** with ECS
2. **Health checks** ensure new version is healthy
3. **Gradual traffic shifting** via ALB
4. **Automatic rollback** if issues detected

## Next Steps

1. **Create Dockerfile and test locally**
2. **Set up MongoDB Atlas cluster**
3. **Build Terraform infrastructure modules**
4. **Configure CI/CD pipeline**
5. **Deploy to staging environment first**
6. **Production deployment with monitoring**

This strategy provides a production-ready, scalable, and cost-effective deployment that can handle growth while maintaining high availability and security.
