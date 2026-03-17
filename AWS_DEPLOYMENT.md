# AWS Deployment Guide for Cartoonify App

## Prerequisites
- AWS CLI installed and configured
- Docker installed
- AWS account with appropriate permissions

## Option 1: AWS Elastic Beanstalk (Recommended)

### 1. Initialize EB CLI
```bash
pip install awsebcli
eb init -p "Docker running on 64bit Amazon Linux 2" cartoonify-app
```

### 2. Create Application
```bash
eb create cartoonify-prod
```

### 3. Deploy
```bash
eb deploy
```

### 4. Open Application
```bash
eb open
```

## Option 2: AWS App Runner

### 1. Build and Push Docker Image
```bash
# Build Docker image
docker build -t cartoonify-app .

# Tag for ECR
aws ecr create-repository --repository-name cartoonify-app
docker tag cartoonify-app:latest <aws-account-id>.dkr.ecr.<region>.amazonaws.com/cartoonify-app:latest

# Push to ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <aws-account-id>.dkr.ecr.<region>.amazonaws.com
docker push <aws-account-id>.dkr.ecr.<region>.amazonaws.com/cartoonify-app:latest
```

### 2. Create App Runner Service
```bash
aws apprunner create-service \
    --service-name cartoonify-app \
    --source-configuration '{
        "ImageRepository": {
            "ImageIdentifier": "<aws-account-id>.dkr.ecr.<region>.amazonaws.com/cartoonify-app:latest",
            "ImageRepositoryType": "ECR"
        }
    }' \
    --instance-configuration 'Cpu=512,Memory=1024' \
    --auto-scaling-configuration-arn 'arn:aws:apprunner:<region>:<aws-account-id>:autoscalingconfiguration/DefaultConfiguration/1/0000000000000000000000000001'
```

## Option 3: EC2 with Docker

### 1. Create EC2 Instance
```bash
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t2.micro \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx \
    --user-data file://user-data.sh
```

### 2. User Data Script (user-data.sh)
```bash
#!/bin/bash
yum update -y
yum install -y docker
service docker start
usermod -a -G docker ec2-user

# Install docker-compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone and run application
cd /home/ec2-user
git clone <your-repo-url>
cd <repo-name>
docker-compose up -d
```

## Environment Variables
- `PORT`: Application port (default: 5000)
- `DEBUG`: Debug mode (default: 0)

## Security Considerations
1. Configure security groups to allow HTTP (port 80) and HTTPS (port 443)
2. Set up SSL/TLS certificates
3. Enable AWS WAF for protection
4. Configure S3 for static file storage in production
5. Set up CloudFront for CDN

## Monitoring
- Enable CloudWatch monitoring
- Set up CloudWatch alarms for CPU/memory usage
- Configure application health checks

## Cost Optimization
- Use auto-scaling groups
- Enable spot instances for non-critical workloads
- Set up lifecycle policies for S3 buckets
