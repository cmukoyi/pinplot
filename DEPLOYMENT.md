# GPS Tracker Deployment Guide

Complete guide for deploying the GPS Tracker application to Digital Ocean with CI/CD.

## 🎯 Overview

This deployment setup includes:
- Automated CI/CD with GitHub Actions
- Docker containerization for all services
- PostgreSQL database
- Nginx reverse proxy
- Automated SSL certificates (can be added)
- Backend API, Admin Dashboard, and Customer Dashboard

## 📋 Prerequisites

1. **Digital Ocean Account**
   - Create a droplet (Ubuntu 22.04 LTS recommended)
   - Minimum: 2GB RAM, 2 vCPUs, 50GB SSD

2. **GitHub Account**
   - Repository for your code
   - GitHub Actions enabled

3. **SendGrid Account (Recommended for Email Notifications)**
   - Free tier: 100 emails/day
   - Setup guide: [SENDGRID_SETUP.md](SENDGRID_SETUP.md)
   - Alternative: Use SMTP (Gmail, etc.)

4. **Domain Name (Optional but recommended)**
   - For production use with SSL

## 🚀 Quick Start Deployment

### Step 1: Setup Digital Ocean Server

1. Create a new Ubuntu 22.04 droplet on Digital Ocean
2. SSH into your server:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

3. Run the setup script:
   ```bash
   curl -o setup-digital-ocean.sh https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/deploy/setup-digital-ocean.sh
   chmod +x setup-digital-ocean.sh
   ./setup-digital-ocean.sh
   ```

   Or manually run:
   ```bash
   # Update system
   sudo apt-get update && sudo apt-get upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   
   # Configure firewall
   sudo ufw allow OpenSSH
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 5001/tcp
   sudo ufw allow 3000/tcp
   sudo ufw allow 3001/tcp
   sudo ufw --force enable
   ```

### Step 2: Configure GitHub Repository

1. **Initialize Git (if not already done)**
   ```bash
   cd /Users/carl/Documents/MobileCode/mobileGPS
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Add GitHub Secrets**
   
   Go to your GitHub repository → Settings → Secrets and variables → Actions
   
   Add these secrets:
   
   | Secret Name | Description | Example |
   |------------|-------------|---------|
   | `DO_SERVER_IP` | Your Digital Ocean droplet IP | `165.232.123.45` |
   | `DO_USER` | SSH user on server | `root` |
   | `DO_SSH_PRIVATE_KEY` | SSH private key for server access | (contents of ~/.ssh/id_rsa) |
   | `SECRET_KEY` | Django/FastAPI secret key | Generate: `openssl rand -hex 32` |
   | `DATABASE_URL` | PostgreSQL connection string | `postgresql://gpsuser:password@postgres:5432/gpsdb` |
   | `MZONE_CLIENT_ID` | MZone API client ID | Your MZone credentials |
   | `MZONE_CLIENT_SECRET` | MZone API client secret | Your MZone credentials |
   | `MPROFILER_USERNAME` | MProfiler API username | Your MProfiler username |
   | `MPROFILER_PASSWORD` | MProfiler API password | Your MProfiler password |
   | `SENDGRID_API_KEY` | SendGrid API key for emails | Get from SendGrid dashboard (see SENDGRID_SETUP.md) |
   | `FROM_EMAIL` | Verified sender email address | `noreply@yourdomain.com` |

3. **Generate SSH Key for GitHub Actions**
   
   On your Digital Ocean server:
   ```bash
   ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions -N ""
   cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
   cat ~/.ssh/github_actions  # Copy this to DO_SSH_PRIVATE_KEY secret
   ```

### Step 3: Configure Environment on Server

SSH to your server and create the `.env` file:

```bash
ssh root@YOUR_SERVER_IP
cd ~/gps-tracker/gps-tracker/backend

cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://gpsuser:yourpassword@postgres:5432/gpsdb

# Email Configuration - SendGrid (Recommended)
# Get API key from: https://app.sendgrid.com/settings/api_keys
# See SENDGRID_SETUP.md for detailed setup instructions
SENDGRID_API_KEY=SG.your-sendgrid-api-key-here
FROM_EMAIL=noreply@yourdomain.com

# SMTP Fallback (optional - only if not using SendGrid)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=True

MZONE_BASE_URL=https://api.mzoneweb.net
MZONE_CLIENT_ID=your-client-id
MZONE_CLIENT_SECRET=your-client-secret
MZONE_TOKEN_URL=https://login.mzoneweb.net/connect/token
MZONE_API_TIMEOUT=30
MPROFILER_BASE_URL=https://live.scopemp.net/Scope.MProfiler.Api
MPROFILER_USERNAME=your-username
MPROFILER_PASSWORD=your-password
ALLOWED_ORIGINS=*
BACKEND_HOST=0.0.0.0
BACKEND_PORT=5001
EOF
```

Update the PostgreSQL password in `docker-compose.yml` to match your `DATABASE_URL`.

### Step 4: Deploy

#### Option A: Automatic Deployment (Recommended)

Simply push to main branch:
```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

GitHub Actions will automatically deploy to your server.

#### Option B: Manual Deployment

```bash
cd /Users/carl/Documents/MobileCode/mobileGPS/deploy
chmod +x deploy-manual.sh
./deploy-manual.sh YOUR_SERVER_IP root
```

## 🔍 Verify Deployment

After deployment, check these URLs:

- **Backend API**: `http://YOUR_SERVER_IP:5001/docs`
- **Backend Health**: `http://YOUR_SERVER_IP:5001/health`
- **Admin Dashboard**: `http://YOUR_SERVER_IP:3000`
- **Customer Dashboard**: `http://YOUR_SERVER_IP:3001`

## 📱 Mobile App Configuration

Update the backend URL in your Flutter mobile app:

```dart
// lib/services/auth_service.dart or similar
static const String baseUrl = 'http://YOUR_SERVER_IP:5001';
```

Rebuild and redistribute the mobile app.

## 🔒 Production Security Checklist

- [ ] Change all default passwords
- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY`
- [ ] Configure firewall (UFW)
- [ ] Setup SSL certificates (Let's Encrypt)
- [ ] Restrict CORS origins (don't use `*`)
- [ ] Regular backups of database
- [ ] Monitor logs and errors
- [ ] Keep Docker images updated
- [ ] Use environment-specific secrets

## 🔄 Common Operations

### View Logs
```bash
ssh root@YOUR_SERVER_IP
cd ~/gps-tracker/gps-tracker
docker-compose logs -f backend
docker-compose logs -f admin-dashboard
docker-compose logs -f customer-dashboard
```

### Restart Services
```bash
ssh root@YOUR_SERVER_IP
cd ~/gps-tracker/gps-tracker
docker-compose restart
```

### Update Services
```bash
ssh root@YOUR_SERVER_IP
cd ~/gps-tracker/gps-tracker
git pull
docker-compose down
docker-compose up -d --build
```

### Backup Database
```bash
ssh root@YOUR_SERVER_IP
cd ~/gps-tracker/gps-tracker
docker-compose exec postgres pg_dump -U gpsuser gpsdb > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database
```bash
cat backup_file.sql | ssh root@YOUR_SERVER_IP "cd ~/gps-tracker/gps-tracker && docker-compose exec -T postgres psql -U gpsuser gpsdb"
```

## 🐛 Troubleshooting

### Containers not starting
```bash
docker-compose logs
docker-compose ps
```

### Permission denied errors
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Database connection issues
- Check `DATABASE_URL` in `.env`
- Verify PostgreSQL container is running: `docker-compose ps`
- Check PostgreSQL logs: `docker-compose logs postgres`

### API not responding
- Check backend logs: `docker-compose logs backend`
- Verify firewall: `sudo ufw status`
- Test locally on server: `curl http://localhost:5001/health`

## 🌐 Domain Setup (Optional)

1. Point your domain to your Digital Ocean IP
2. Update nginx configuration for your domain
3. Install SSL certificate:
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

## 📊 Monitoring

Consider setting up:
- Digital Ocean Monitoring (built-in)
- Uptime monitoring (UptimeRobot, Pingdom)
- Log aggregation (ELK stack, Grafana)
- Error tracking (Sentry)

## 🆘 Support

- Check GitHub Issues
- Review application logs
- Contact development team

## 📝 Version History

- v1.0.0 - Initial production deployment setup
