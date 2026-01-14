# EC2 Deployment Guide

Complete guide to deploy the Lung Transplant Visualization app on AWS EC2.

## Prerequisites

- AWS account with EC2 access
- GitHub repository with your code
- SSH key pair for EC2

---

## Step 1: Push to GitHub

On your local machine:

```bash
cd /Users/andysun/Desktop/BMI706_SRTR_LUNG

# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for EC2 deployment"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/BMI706_SRTR_LUNG.git

# Push
git push -u origin main
```

---

## Step 2: Launch EC2 Instance

1. **Go to AWS Console** → EC2 → Launch Instance

2. **Settings:**
   - Name: `bmi706-lung-transplant`
   - AMI: Amazon Linux 2023 or Ubuntu 22.04 LTS
   - Instance type: `t2.small` (recommended) or `t2.micro` (free tier)
   - Key pair: Select or create one
   - Security Group: Allow these ports:
     - SSH (22) - Your IP only
     - HTTP (80) - Anywhere (0.0.0.0/0)
     - HTTPS (443) - Anywhere (optional)

3. **Storage:** 20 GB (8 GB minimum)

4. **Launch** and note your Public IP

---

## Step 3: Connect to EC2

```bash
# On your local machine
ssh -i ~/.ssh/your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP

# If Ubuntu:
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

---

## Step 4: Install Docker on EC2

**For Amazon Linux 2023:**
```bash
# Update system
sudo dnf update -y

# Install Docker
sudo dnf install docker -y

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Apply group changes (or logout/login)
newgrp docker
```

**For Ubuntu:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Apply group changes
newgrp docker
```

---

## Step 5: Clone and Deploy

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/BMI706_SRTR_LUNG.git
cd BMI706_SRTR_LUNG

# Build and start containers
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## Step 6: Access Your App

Open your browser and go to:
```
http://YOUR_EC2_PUBLIC_IP
```

---

## Useful Commands

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx

# Restart all services
docker-compose restart

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up --build -d

# Check disk usage
docker system df

# Clean unused images
docker system prune -a
```

---

## Updating the App

When you push new changes to GitHub:

```bash
# On EC2
cd ~/BMI706_SRTR_LUNG

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up --build -d
```

---

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Check if ports are in use
sudo netstat -tulpn | grep :80
```

### Out of memory (t2.micro)
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

### Permission denied
```bash
# Re-add to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

## Cost Estimate (Monthly)

| Resource | Free Tier | After Free Tier |
|----------|-----------|-----------------|
| t2.micro | $0 (750h/mo) | ~$8.50 |
| t2.small | N/A | ~$17 |
| EBS 20GB | $0 (30GB free) | ~$2 |
| Data Transfer | 100GB free | $0.09/GB |

---

## Security Notes

1. **Never expose SSH (port 22)** to 0.0.0.0/0
2. Keep your `.pem` key safe and private
3. Consider setting up HTTPS with Let's Encrypt for production
