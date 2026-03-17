#!/bin/bash

# AWS EC2 User Data Script for Cartoonify App

yum update -y

# Install Docker
yum install -y docker
service docker start
usermod -a -G docker ec2-user

# Install Git
yum install -y git

# Install docker-compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/cartoonify
cd /opt/cartoonify

# Clone your repository (replace with your actual repo URL)
# git clone https://github.com/yourusername/cartoonify.git .

# For now, we'll assume you'll copy the files manually
# Create necessary directories
mkdir -p static/uploads static/results

# Build and run Docker container
docker build -t cartoonify-app .
docker run -d -p 80:5000 --name cartoonify-container cartoonify-app

# Enable auto-start on boot
echo 'docker start cartoonify-container' >> /etc/rc.local
chmod +x /etc/rc.local
