# Beacon Telematics - Quick Start Guide

## What Was Created

A complete copy of your GPS tracker application has been created at:
**`/Users/carl/Documents/MobileCode/beaconTelematics`**

All naming has been updated to use **"beacon_telematics"** prefix to differentiate from the production "mobileGPS" instance.

## Changes Made

### 1. Docker Container Names
All containers now use the `beacon_telematics_*` prefix:
- `beacon_telematics_db` 
- `beacon_telematics_backend` 
- `beacon_telematics_admin` 
- `beacon_telematics_customer` 
- `beacon_telematics_flutter_web` 
- `beacon_telematics_nginx`

### 2. Database Configuration
- **Database Name**: `beacon_telematics` (changed from `ble_tracker`)
- **Database User**: `beacon_user` (changed from `ble_user`)
- **Database Password**: `beacon_password` (default for local dev)
- **Volume Name**: `beacon_telematics_postgres_data`

### 3. Network Configuration
- **Network Name**: `beacon_telematics_network` (changed from `ble_network`)
- **Local Network**: `beacon_telematics_network_local`

### 4. Files Updated
✅ `gps-tracker/docker-compose.yml` - Production-like setup with new naming
✅ `gps-tracker/docker-compose.local.yml` - Local development setup with new naming
✅ `gps-tracker/.env.example` - Template with new database names
✅ `gps-tracker/.env` - Ready to use with new database configuration
✅ `gps-tracker/backend/.env.example` - Backend template with new DATABASE_URL

## Running the BeaconTelematics Instance Locally

### Option 1: Local Development (Recommended)
```bash
cd /Users/carl/Documents/MobileCode/beaconTelematics/gps-tracker

# Create backend .env from example (if not exists)
cp backend/.env.example backend/.env

# Edit backend/.env and add:
# - SECRET_KEY (generate a secure 32+ char string)
# - SENDGRID_API_KEY (if you want email functionality)
# - MZONE credentials

# Start all services
docker-compose -f docker-compose.local.yml up --build

# Access:
# - Backend: http://localhost:8000
# - Admin Dashboard: http://localhost:3000
# - Customer Dashboard: http://localhost:3001
# - Flutter Web: http://localhost:3002
```

### Option 2: Production-like Setup
```bash
cd /Users/carl/Documents/MobileCode/beaconTelematics/gps-tracker

# Configure backend/.env first (same as above)

# Start with nginx
docker-compose up --build
```

## Running Both Instances Simultaneously

Since the container names are now different, both instances can run at the same time **IF** you modify the ports in one of them.

To run both simultaneously, edit `beaconTelematics/gps-tracker/docker-compose.yml` and change the ports:

```yaml
services:
  db:
    ports:
      - "5433:5432"  # Changed from 5432
  
  backend:
    ports:
      - "8001:8000"  # Changed from 8000
  
  admin:
    ports:
      - "3010:3000"  # Changed from 3000
  
  customer:
    ports:
      - "3011:3001"  # Changed from 3001
  
  flutter-web:
    ports:
      - "3012:80"    # Changed from 3002
  
  nginx:
    ports:
      - "8080:80"    # Changed from 80
      - "8443:443"   # Changed from 443
```

## Database Management

### Initialize Database
```bash
cd /Users/carl/Documents/MobileCode/beaconTelematics/gps-tracker

# Run Alembic migrations
docker-compose exec backend alembic upgrade head
```

### Access Database
```bash
# Connect to PostgreSQL
docker exec -it beacon_telematics_db psql -U beacon_user -d beacon_telematics
```

### Reset Database (if needed)
```bash
# Stop containers
docker-compose down

# Remove volume
docker volume rm beacon_telematics_postgres_data

# Start fresh
docker-compose up --build
```

## Verify Everything Works

1. **Check all containers are running:**
   ```bash
   docker ps | grep beacon_telematics
   ```

2. **Test backend API:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. **View logs:**
   ```bash
   cd /Users/carl/Documents/MobileCode/beaconTelematics/gps-tracker
   
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f backend
   ```

## Key Differences from Production (mobileGPS)

| Aspect | Production (mobileGPS) | Local (beaconTelematics) |
|--------|------------------------|--------------------------|
| Container Prefix | `ble_tracker_*` | `beacon_telematics_*` |
| Database Name | `ble_tracker` | `beacon_telematics` |
| Database User | `ble_user` | `beacon_user` |
| Network Name | `ble_network` | `beacon_telematics_network` |
| Volume Name | `postgres_data` | `beacon_telematics_postgres_data` |
| Location | `/root/gps-tracker` (server) | `/Users/carl/Documents/MobileCode/beaconTelematics` |

## Next Steps

1. **Create backend/.env file:**
   ```bash
   cd /Users/carl/Documents/MobileCode/beaconTelematics/gps-tracker/backend
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Generate JWT Secret Key:**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   # Add this to backend/.env as SECRET_KEY
   ```

3. **Start the application:**
   ```bash
   cd /Users/carl/Documents/MobileCode/beaconTelematics/gps-tracker
   docker-compose -f docker-compose.local.yml up --build
   ```

4. **Run database migrations:**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Access the application:**
   - Backend API: http://localhost:8000/docs (Swagger UI)
   - Admin Dashboard: http://localhost:3000
   - Customer Dashboard: http://localhost:3001
   - Flutter Web App: http://localhost:3002

## Troubleshooting

### Port Already in Use
If ports are already in use by the production instance, follow the "Running Both Instances Simultaneously" section above.

### Database Connection Errors
Ensure the DATABASE_URL in `backend/.env` matches:
```
DATABASE_URL=postgresql://beacon_user:beacon_password@db:5432/beacon_telematics
```

### Container Name Conflicts
If you see container name conflicts, ensure you're in the correct directory:
- Production: `/root/gps-tracker` (on server)
- Local: `/Users/carl/Documents/MobileCode/beaconTelematics`

Both can run simultaneously because container names are different.

## Support Files

- 📖 **LOCAL_INSTANCE_README.md** - Overview of differences
- 📋 **QUICK_START.md** - This file
- 📚 All original documentation files are copied

Enjoy your local BeaconTelematics development instance! 🚀
