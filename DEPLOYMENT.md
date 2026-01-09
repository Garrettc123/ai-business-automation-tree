# Deployment Guide

This guide provides comprehensive instructions for deploying the AI Business Automation Tree system in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Vercel Deployment](#vercel-deployment)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

- **Docker**: Version 20.10+ with Docker Compose v2+
- **Python**: Version 3.10 or 3.11 (for local development)
- **Git**: For cloning the repository
- **API Keys**: OpenAI, Anthropic, or other AI service credentials

## Local Development

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Garrettc123/ai-business-automation-tree.git
cd ai-business-automation-tree

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and configuration

# Run the application
python main.py
```

The application will start on `http://localhost:8000`

### Endpoints

- Health Check: `http://localhost:8000/health`
- System Status: `http://localhost:8000/api/status`
- Branches Info: `http://localhost:8000/api/branches`

## Docker Deployment

### Option 1: Using Setup Script (Recommended)

```bash
# Run the automated setup
chmod +x setup.sh
./setup.sh
```

The script will:
- Check for Docker installation
- Create `.env` from template
- Pull required images
- Build the application
- Start all services

### Option 2: Manual Docker Compose

```bash
# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Build and start services
docker compose build
docker compose up -d

# View logs
docker compose logs -f

# Check service status
docker compose ps
```

### Accessing Services

- **Application**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/changeme)
- **Prometheus**: http://localhost:9090
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **MongoDB**: localhost:27017

## Cloud Deployment

### Remote Server Deployment

Use the provided script for deployment to AWS, GCP, Azure, or any VPS:

```bash
chmod +x deploy-to-cloud.sh
./deploy-to-cloud.sh
```

You'll be prompted for:
- Server hostname/IP
- SSH username
- SSH port (default: 22)

The script will:
1. Test SSH connection
2. Copy files to the server
3. Install Docker (if needed)
4. Run the setup script remotely
5. Start all services

### Manual Cloud Deployment

```bash
# SSH into your server
ssh user@your-server.com

# Clone the repository
git clone https://github.com/Garrettc123/ai-business-automation-tree.git
cd ai-business-automation-tree

# Run setup
./setup.sh
```

### Production Considerations

1. **SSL/TLS**: Configure SSL certificates in `nginx.conf`
   ```nginx
   ssl_certificate /etc/nginx/certs/fullchain.pem;
   ssl_certificate_key /etc/nginx/certs/privkey.pem;
   ```

2. **Environment Variables**: Update production values
   ```bash
   # Database passwords
   DB_PASSWORD=<strong-password>
   REDIS_PASSWORD=<strong-password>
   MONGO_PASSWORD=<strong-password>
   
   # API keys
   OPENAI_API_KEY=<your-key>
   
   # Security
   SECRET_KEY=<random-secret>
   JWT_SECRET_KEY=<random-secret>
   ```

3. **Firewall**: Configure firewall rules
   ```bash
   # Allow HTTP/HTTPS
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   
   # Allow SSH
   sudo ufw allow 22/tcp
   
   # Enable firewall
   sudo ufw enable
   ```

## Vercel Deployment

For serverless API deployment:

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

Configure environment variables in Vercel dashboard:
- `OPENAI_API_KEY`
- `DB_HOST`, `DB_PASSWORD`, etc.
- Other required variables from `.env.example`

**Note**: Vercel deployment is suitable for the API layer only. For full stack with databases, use Docker deployment.

## Verification

### Automated Verification

```bash
chmod +x verify-deployment.sh
./verify-deployment.sh
```

This checks:
- Python syntax
- Docker Compose configuration
- Nginx configuration
- Required files and directories
- Script permissions
- Health endpoint (if running)

### Manual Verification

1. **Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **System Status**:
   ```bash
   curl http://localhost:8000/api/status
   ```

3. **Docker Services**:
   ```bash
   docker compose ps
   ```

4. **Service Logs**:
   ```bash
   docker compose logs app
   docker compose logs postgres
   docker compose logs redis
   ```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port 8000
sudo lsof -i :8000
# or
sudo netstat -tulpn | grep 8000

# Stop the process
sudo kill -9 <PID>
```

#### 2. Docker Build Fails

```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker compose build --no-cache
```

#### 3. Database Connection Issues

```bash
# Check database logs
docker compose logs postgres

# Verify database is healthy
docker compose ps postgres

# Restart database
docker compose restart postgres
```

#### 4. Permission Denied

```bash
# Fix script permissions
chmod +x setup.sh deploy-to-cloud.sh verify-deployment.sh

# Fix data directories
sudo chown -R $USER:$USER logs/ data/ models/
```

#### 5. SSL Certificate Issues

For production with SSL:
```bash
# Using Let's Encrypt
sudo certbot --nginx -d yourdomain.com

# Or generate self-signed certificate (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/privkey.pem -out certs/fullchain.pem
```

### Getting Help

- Check logs: `docker compose logs -f`
- View service status: `docker compose ps`
- Restart services: `docker compose restart`
- Full reset: `docker compose down -v && docker compose up -d`

For more help:
- [GitHub Issues](https://github.com/Garrettc123/ai-business-automation-tree/issues)
- [Documentation](https://github.com/Garrettc123/ai-business-automation-tree)

## Maintenance

### Backup

```bash
# Backup databases
docker compose exec postgres pg_dump -U admin ai_automation > backup.sql
docker compose exec mongodb mongodump --out /data/backups

# Backup data volumes
docker compose down
tar -czf backup.tar.gz logs/ data/ models/
docker compose up -d
```

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose build
docker compose up -d
```

### Scaling

```bash
# Scale Celery workers
docker compose up -d --scale celery-worker=3

# View scaled services
docker compose ps
```

## Security Checklist

- [ ] Change all default passwords
- [ ] Generate secure random secrets
- [ ] Configure SSL/TLS certificates
- [ ] Enable firewall rules
- [ ] Restrict database access
- [ ] Set up automated backups
- [ ] Configure monitoring and alerts
- [ ] Review and update `.env` file
- [ ] Enable audit logging
- [ ] Configure rate limiting

## Performance Optimization

1. **Database**: Increase connection pool size
2. **Redis**: Configure memory limits and eviction policy
3. **Celery**: Scale workers based on load
4. **Nginx**: Enable caching and compression
5. **Application**: Tune worker processes and threads

For production deployments with high load, consider:
- Kubernetes for orchestration
- Load balancer (nginx, HAProxy, AWS ELB)
- Database read replicas
- Redis cluster
- CDN for static assets
