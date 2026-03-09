# Beacon Telematics - Server Setup & Deployment Guide

Complete guide for deploying BeaconTelematics to your production server alongside the existing mobileGPS instance.

## Overview

- **Domain**: beacontelematics.co.uk
- **Server**: ubuntu-s-1vcpu-512mb-10gb-lon1-01 (161.35.38.209)
- **Deployment Path**: `/root/beacon-telematics/`
- **Deployment Method**: GitHub Actions (automated on push to main)

## Port Allocation

BeaconTelematics uses different ports to avoid conflicts with mobileGPS:

| Service | Port | mobileGPS Port |
|---------|------|----------------|
| PostgreSQL | 5433 | 5432 |
| Backend API | 8001 | 8000 |
| Admin Dashboard | 3010 | 3000 |
| Customer Dashboard | 3011 | 3001 |
| Flutter Web | 3012 | 3002 |

## Prerequisites

### 1. DNS Configuration

You need to point beacontelematics.co.uk to your server IP **before** SSL setup:

**A Records to create:**
```
Type: A
Name: @
Value: 161.35.38.209
TTL: 3600

Type: A
Name: www
Value: 161.35.38.209
TTL: 3600
```

**Verify DNS propagation:**
```bash
# On your local machine
dig beacontelematics.co.uk
dig www.beacontelematics.co.uk
```

Wait for DNS to propagate (can take 5 minutes to 48 hours depending on provider).

### 2. GitHub Repository Setup

The beaconTelematics folder needs to be its own repository to deploy independently:

```bash
# On your local machine
cd /Users/carl/Documents/MobileCode/beaconTelematics

# Initialize git repository
git init
git add .
git commit -m "Initial BeaconTelematics setup"

# Create new GitHub repository (beaconTelematics) and push
git remote add origin git@github.com:cmukoyi/beaconTelematics.git
git branch -M main
git push -u origin main
```

### 3. GitHub Secrets Configuration

Add the same secrets used for mobileGPS deployment:

Go to: `https://github.com/cmukoyi/beaconTelematics/settings/secrets/actions`

**Required Secrets:**
- `DO_SSH_PRIVATE_KEY` - Your SSH private key for the server
- `DO_SERVER_IP` - `161.35.38.209`
- `DO_USER` - `root`

## Server Setup Steps

SSH to your server and follow these steps:

```bash
ssh root@161.35.38.209
```

### Step 1: Create Directory Structure

```bash
# Create BeaconTelematics directory
mkdir -p ~/beacon-telematics/gps-tracker
mkdir -p ~/beacon-telematics-backups

# Verify structure
ls -la ~/beacon-telematics/
```

### Step 2: Create Environment Files

#### Root Environment File

```bash
nano ~/beacon-telematics/gps-tracker/.env
```

Add the following:
```env
# Database Configuration
POSTGRES_USER=beacon_user
POSTGRES_PASSWORD=<GENERATE_SECURE_PASSWORD>
POSTGRES_DB=beacon_telematics

# MZone Client Secret
MZONE_CLIENT_SECRET=g_SkQ.B.z3TeBU$g#hVeP#c2
```

**Generate secure password:**
```bash
openssl rand -base64 32
```

#### Backend Environment File

```bash
nano ~/beacon-telematics/gps-tracker/backend/.env
```

Add the following:
```env
# Database Configuration
DATABASE_URL=postgresql://beacon_user:<SAME_PASSWORD_AS_ABOVE>@db:5432/beacon_telematics

# JWT Secret Key (generate a secure random string, min 32 chars)
SECRET_KEY=<GENERATE_SECURE_SECRET>

# SendGrid Email Configuration
SENDGRID_API_KEY=<YOUR_SENDGRID_API_KEY>
FROM_EMAIL=noreply@beacontelematics.co.uk

# MZone API Configuration
MZONE_API_URL=https://api.myprofiler.com/oauth2/v1
MZONE_REDIRECT_URI=https://beacontelematics.co.uk/api/v1/mzone/callback
MZONE_CLIENT_ID=Tracking_GPS
MZONE_CLIENT_SECRET=g_SkQ.B.z3TeBU$g#hVeP#c2

# Optional Settings
DEBUG=False
ENVIRONMENT=production
```

**Generate JWT Secret Key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Important:** 
- Use the SAME database password in both `.env` files
- Generate a NEW and UNIQUE `SECRET_KEY` (different from mobileGPS)
- Create a SendGrid account if you don't have one, or use the same API key as mobileGPS

### Step 3: Configure Nginx for beacontelematics.co.uk

```bash
# Copy the nginx config (will be present after first deployment)
# Or create it manually now:
nano /etc/nginx/sites-available/beacontelematics.co.uk
```

Paste this configuration:
```nginx
server {
    listen 80;
    server_name beacontelematics.co.uk www.beacontelematics.co.uk;
    
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /admin {
        proxy_pass http://localhost:3010;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /customer {
        proxy_pass http://localhost:3011;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location / {
        proxy_pass http://localhost:3012;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Enable the site:**
```bash
# Create symlink
ln -s /etc/nginx/sites-available/beacontelematics.co.uk /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

# Reload nginx
systemctl reload nginx
```

### Step 4: Setup SSL Certificate (AFTER DNS propagates)

Wait for DNS to propagate, then run certbot:

```bash
# Install certbot (if not already installed)
apt update
apt install certbot python3-certbot-nginx -y

# Get SSL certificate for beacontelematics.co.uk
certbot --nginx -d beacontelematics.co.uk -d www.beacontelematics.co.uk

# Follow the prompts:
# - Enter your email
# - Agree to terms
# - Choose whether to redirect HTTP to HTTPS (recommended: yes)
```

Certbot will automatically:
- Generate SSL certificates
- Update your nginx configuration
- Setup auto-renewal

**Verify SSL:**
```bash
certbot certificates
```

### Step 5: Initial Manual Deployment (First Time Only)

Since GitHub Actions will handle deployment going forward, we need to do a one-time manual setup:

**Option A: Wait for GitHub Actions (Recommended)**

After you've:
1. Created the beaconTelematics GitHub repository
2. Added GitHub Secrets
3. Pushed the code

GitHub Actions will automatically deploy. Monitor at:
`https://github.com/cmukoyi/beaconTelematics/actions`

**Option B: Manual First Deployment**

If you want to deploy immediately:

```bash
# Clone the repository (after you've pushed to GitHub)
cd ~
git clone git@github.com:cmukoyi/beaconTelematics.git beacon-telematics-temp

# Copy to deployment location
cp -r beacon-telematics-temp/gps-tracker/* ~/beacon-telematics/gps-tracker/

# Build and start containers
cd ~/beacon-telematics/gps-tracker
docker-compose build
docker-compose up -d

# Wait for containers to start
sleep 30

# Check status
docker-compose ps

# Run database migrations
docker-compose exec backend alembic upgrade head
```

### Step 6: Verify Deployment

```bash
# Check all BeaconTelematics containers are running
docker ps | grep beacon_telematics

# Should see 5 containers:
# - beacon_telematics_db
# - beacon_telematics_backend
# - beacon_telematics_admin
# - beacon_telematics_customer
# - beacon_telematics_flutter_web

# Check backend health
curl http://localhost:8001/api/health

# Check Flutter web
curl -I http://localhost:3012/

# Check via domain (after DNS/SSL setup)
curl https://beacontelematics.co.uk/api/health
```

### Step 7: Check Logs

```bash
# View all logs
cd ~/beacon-telematics/gps-tracker
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f flutter-web

# View last 50 lines
docker-compose logs --tail=50 backend
```

## Post-Deployment Tasks

### Database Initialization

```bash
cd ~/beacon-telematics/gps-tracker

# Run Alembic migrations
docker-compose exec backend alembic upgrade head

# Verify database
docker exec -it beacon_telematics_db psql -U beacon_user beacon_telematics

# Inside psql:
\dt  # List tables
\q   # Quit
```

### Create First User (Optional)

```bash
# Access backend container
docker-compose exec backend python

# In Python shell:
from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext

db = SessionLocal()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

user = User(
    email="admin@beacontelematics.co.uk",
    hashed_password=pwd_context.hash("ChangeMe123!"),
    is_active=True,
    is_verified=True
)
db.add(user)
db.commit()
print("User created!")
exit()
```

## Continuous Deployment

Once setup is complete, deployments are **automatic**:

1. Make changes locally in `beaconTelematics/`
2. Commit and push to GitHub:
   ```bash
   cd /Users/carl/Documents/MobileCode/beaconTelematics
   git add .
   git commit -m "Your change description"
   git push
   ```
3. GitHub Actions automatically deploys to production
4. Monitor at: `https://github.com/cmukoyi/beaconTelematics/actions`

## Monitoring & Maintenance

### View Container Status
```bash
docker ps | grep beacon_telematics
```

### Restart Services
```bash
cd ~/beacon-telematics/gps-tracker

# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Update Containers (Manual)
```bash
cd ~/beacon-telematics/gps-tracker
git pull  # If you're tracking the repo here
docker-compose down
docker-compose build
docker-compose up -d
```

### Database Backup
```bash
# Manual backup
docker exec beacon_telematics_db pg_dump -U beacon_user beacon_telematics > ~/beacon-telematics-backups/manual-backup-$(date +%Y%m%d-%H%M%S).sql

# Restore from backup
docker exec -i beacon_telematics_db psql -U beacon_user beacon_telematics < ~/beacon-telematics-backups/your-backup.sql
```

### Rollback Deployment
```bash
~/beacon-telematics/rollback-deployment-beacon.sh
```

## Troubleshooting

### Ports Already in Use
```bash
# Check what's using a port
lsof -i :8001
netstat -tulpn | grep 8001

# If mobileGPS is using the same port, verify docker-compose.yml has correct port mappings
```

### Container Won't Start
```bash
# Check logs
docker-compose logs backend

# Check if database is ready
docker-compose logs db

# Restart specific container
docker-compose restart backend
```

### Database Connection Issues
```bash
# Verify DATABASE_URL in backend/.env matches:
# postgresql://beacon_user:<PASSWORD>@db:5432/beacon_telematics

# Check database container
docker exec -it beacon_telematics_db psql -U beacon_user beacon_telematics

# Inside psql, verify:
\l  # List databases - should see beacon_telematics
```

### SSL Certificate Issues
```bash
# Check certificates
certbot certificates

# Renew manually (cron usually handles this)
certbot renew

# Test renewal
certbot renew --dry-run
```

### DNS Not Resolving
```bash
# Check DNS propagation
dig beacontelematics.co.uk
nslookup beacontelematics.co.uk

# Check nginx is listening
netstat -tulpn | grep :80
netstat -tulpn | grep :443
```

## Security Checklist

- [ ] Unique SECRET_KEY generated (different from mobileGPS)
- [ ] Strong database passwords set
- [ ] SSL certificate installed and auto-renewal enabled
- [ ] Firewall configured (ufw) to allow ports 80, 443, 22
- [ ] GitHub Secrets properly configured
- [ ] SendGrid API key secured
- [ ] MZone credentials secured
- [ ] Backend .env file has DEBUG=False
- [ ] Regular database backups scheduled

## Testing Checklist

After deployment, verify:

- [ ] https://beacontelematics.co.uk loads (Flutter web app)
- [ ] https://beacontelematics.co.uk/api/health returns 200 OK
- [ ] https://beacontelematics.co.uk/admin loads (Admin dashboard)
- [ ] https://beacontelematics.co.uk/customer loads (Customer dashboard)
- [ ] User registration works
- [ ] Email verification works
- [ ] Login works
- [ ] MZone API integration works
- [ ] Geofence alerts work
- [ ] Both mobileGPS and BeaconTelematics run simultaneously

## Support

### Useful Commands
```bash
# SSH to server
ssh root@161.35.38.209

# Navigate to BeaconTelematics
cd ~/beacon-telematics/gps-tracker

# View all services
docker-compose ps

# View logs
docker-compose logs -f

# Restart everything
docker-compose restart

# Stop everything
docker-compose down

# Start everything
docker-compose up -d

# Rebuild and restart
docker-compose down && docker-compose build && docker-compose up -d
```

### Important Paths
- **Deployment**: `/root/beacon-telematics/gps-tracker/`
- **Backups**: `/root/beacon-telematics-backups/`
- **Scripts**: `/root/beacon-telematics/`
- **Nginx Config**: `/etc/nginx/sites-available/beacontelematics.co.uk`
- **SSL Certs**: `/etc/letsencrypt/live/beacontelematics.co.uk/`

### Production URLs
- **Frontend**: https://beacontelematics.co.uk
- **Backend API**: https://beacontelematics.co.uk/api
- **Admin Dashboard**: https://beacontelematics.co.uk/admin
- **Customer Dashboard**: https://beacontelematics.co.uk/customer
- **API Docs**: https://beacontelematics.co.uk/api/docs

### Quick Health Check
```bash
# Run this to verify everything is working
curl -f https://beacontelematics.co.uk/api/health && \
curl -f -I https://beacontelematics.co.uk/ && \
docker ps | grep beacon_telematics && \
echo "✅ All systems operational!"
```

---

## Summary

You now have a complete BeaconTelematics deployment setup that:
- ✅ Runs independently alongside mobileGPS
- ✅ Uses separate domain (beacontelematics.co.uk)
- ✅ Uses different ports (no conflicts)
- ✅ Has separate database and volumes
- ✅ Deploys automatically via GitHub Actions
- ✅ Has backup and rollback scripts
- ✅ Has SSL/HTTPS configured
- ✅ Monitors health and logs

**Next Steps:**
1. Configure DNS for beacontelematics.co.uk
2. Create GitHub repository
3. Push code to GitHub
4. SSH to server and run setup steps above
5. Monitor first deployment via GitHub Actions
