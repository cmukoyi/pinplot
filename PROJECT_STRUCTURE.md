# GPS Tracker Project Structure Guide

**Last Updated:** March 6, 2026  
**Production URL:** https://pinplot.me  
**Production Server:** 161.35.38.209 (ubuntu-s-1vcpu-512mb-10gb-lon1-01)

---

## 📋 Quick Reference

### When You Need To...

| Task | Files to Update | Location |
|------|----------------|----------|
| **Add API endpoint** | `main.py` | `gps-tracker/backend/app/main.py` |
| **Add database model** | `models.py` | `gps-tracker/backend/app/models.py` |
| **Add migration** | Create new file | `gps-tracker/backend/alembic/versions/` |
| **Update dependencies** | `requirements.txt` | `gps-tracker/backend/requirements.txt` |
| **Add service/business logic** | Create in services/ | `gps-tracker/backend/app/services/` |
| **Change routing/SSL** | `nginx.conf` | `gps-tracker/nginx/nginx.conf` |
| **Update Docker services** | `docker-compose.yml` | `gps-tracker/docker-compose.yml` |
| **Update deployment** | `deploy.yml` | `.github/workflows/deploy.yml` |
| **Add environment variable** | `.env.example` | `gps-tracker/backend/.env.example` |

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────┐
│                   Internet/Users                     │
└─────────────────────┬───────────────────────────────┘
                      │ HTTPS (443)
                      ▼
┌─────────────────────────────────────────────────────┐
│         Nginx Reverse Proxy (SSL Termination)       │
│  - pinplot.me/ → Flutter Web                        │
│  - pinplot.me/api/ → Backend API                    │
│  - pinplot.me/admin/ → Admin Dashboard              │
└─────────────┬───────────────┬──────────┬────────────┘
              │               │          │
    ┌─────────▼──────┐  ┌────▼─────┐  ┌▼──────────┐
    │ Flutter Web    │  │  Admin   │  │  Backend  │
    │ (Port 3002)    │  │ (Port    │  │ (Port     │
    │                │  │  3000)   │  │  8000)    │
    └────────────────┘  └──────────┘  └─────┬─────┘
                                             │
                                     ┌───────▼────────┐
                                     │  PostgreSQL    │
                                     │  (Port 5432)   │
                                     └────────────────┘
```

### Container Stack

```yaml
Services Running in Production:
├── ble_tracker_nginx          - Nginx (SSL + reverse proxy)
├── ble_tracker_flutter_web    - Flutter web UI (main app)
├── ble_tracker_admin          - Node.js admin dashboard
├── ble_tracker_customer       - Node.js customer dashboard
├── ble_tracker_backend        - FastAPI Python backend
└── ble_tracker_db             - PostgreSQL 15 database

Note: Redis container removed (was unused security risk)
```

---

## 📁 Detailed Directory Structure

```
mobileGPS/
├── .github/workflows/          # CI/CD automation
│   └── deploy.yml             # Production deployment
│
├── deploy/                     # Deployment scripts
│   ├── deploy-manual.sh       # Manual deployment script
│   └── setup-digital-ocean.sh # Server setup script
│
├── gps-tracker/               # Main application directory
│   │
│   ├── backend/               # 🔥 FASTAPI PYTHON BACKEND
│   │   ├── app/
│   │   │   ├── main.py       # ⭐ MAIN API FILE (58KB)
│   │   │   │                 # Contains ALL endpoints:
│   │   │   │                 # - User auth (register, login, verify)
│   │   │   │                 # - BLE tag management
│   │   │   │                 # - POI (Points of Interest)
│   │   │   │                 # - Geofencing & alerts
│   │   │   │                 # - MZone API integration
│   │   │   │                 # - Location updates from trackers
│   │   │   │
│   │   │   ├── models.py     # SQLAlchemy ORM models
│   │   │   │                 # - User, BLETag, POI, GeofenceAlert
│   │   │   │                 # - VerificationPIN, POITrackerLink
│   │   │   │
│   │   │   ├── auth.py       # JWT authentication
│   │   │   │                 # - Token creation/verification
│   │   │   │                 # - Password hashing
│   │   │   │
│   │   │   ├── database.py   # Database connection
│   │   │   │                 # - PostgreSQL session management
│   │   │   │
│   │   │   ├── schemas/      # Pydantic request/response models
│   │   │   │   └── poi.py    # POI-related schemas
│   │   │   │
│   │   │   └── services/     # Business logic layer
│   │   │       ├── email_service.py      # SendGrid integration
│   │   │       ├── geofence_service.py   # Location monitoring
│   │   │       └── mzone_service.py      # External API integration
│   │   │
│   │   ├── alembic/          # Database migrations
│   │   │   └── versions/     # Migration scripts
│   │   │       ├── 001_add_verification_and_tags.py
│   │   │       ├── 002_add_poi_and_geofence_alerts.py
│   │   │       ├── 003_add_email_alerts_preference.py
│   │   │       └── 004_add_delivery_route_support.py
│   │   │
│   │   ├── .env              # Environment variables (NOT in git)
│   │   ├── .env.example      # Template for environment vars
│   │   ├── requirements.txt  # Python dependencies
│   │   ├── Dockerfile        # Container build instructions
│   │   └── start.sh          # Startup script
│   │
│   ├── admin-dashboard/       # Node.js admin interface
│   │   ├── server.js         # Express server
│   │   ├── public/
│   │   │   ├── index.html    # Admin UI
│   │   │   └── billing.html  # Billing page
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── customer-dashboard/    # Node.js customer interface
│   │   ├── server.js
│   │   ├── public/
│   │   │   └── index.html
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── mobile-app/           # Flutter application
│   │   ├── ble_tracker_app/  # Flutter project
│   │   │   ├── lib/
│   │   │   │   ├── main.dart
│   │   │   │   ├── models/
│   │   │   │   ├── screens/
│   │   │   │   ├── services/
│   │   │   │   ├── widgets/
│   │   │   │   └── theme/
│   │   │   ├── android/
│   │   │   ├── ios/
│   │   │   ├── web/
│   │   │   └── pubspec.yaml
│   │   └── Dockerfile        # Builds Flutter web
│   │
│   ├── nginx/
│   │   └── nginx.conf        # ⭐ ROUTING & SSL CONFIG
│   │                         # - SSL certificates
│   │                         # - Proxy rules
│   │                         # - Path routing
│   │
│   ├── docker-compose.yml    # ⭐ MAIN ORCHESTRATION FILE
│   │                         # Defines all services
│   │
│   └── *.md                  # Documentation files
│
├── *.md                      # Root documentation
└── setup*.sh                 # Setup scripts
```

---

## 🔧 Backend Technology Stack

### Core Framework
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

### Database
- **PostgreSQL 15** - Primary database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations

### Authentication & Security
- **python-jose** - JWT tokens
- **passlib + bcrypt** - Password hashing

### External Integrations
- **SendGrid** - Email service (verification, alerts)
- **MZone API** - GPS tracker data provider
- **HTTPx + Requests** - HTTP clients

### Key Patterns
- **No Redis** - Removed (was unused)
- **RESTful API** - Standard REST endpoints
- **Token-based auth** - JWT in Authorization header
- **Async/await** - Where needed for performance

---

## 🚀 Deployment Process

### Automatic Deployment (GitHub Actions)

**Trigger:** Push to `main` branch

**Workflow:** `.github/workflows/deploy.yml`

**Steps:**
1. Checkout code from GitHub
2. Setup SSH connection to DigitalOcean
3. Sync files via rsync (excludes node_modules, .git, etc.)
4. Create `.env` files from GitHub Secrets
5. SSH into server
6. Run `docker-compose down --remove-orphans`
7. Run `docker-compose up -d --build`
8. Verify deployment with health check

**Required GitHub Secrets:**
- `DO_SERVER_IP` - Server IP address
- `DO_USER` - SSH username
- `DO_SSH_PRIVATE_KEY` - SSH key for authentication
- `POSTGRES_PASSWORD` - Database password
- `SECRET_KEY` - JWT secret
- `SENDGRID_API_KEY` - Email service key
- `FROM_EMAIL` - Sender email address
- `MZONE_CLIENT_SECRET` - External API secret

### Manual Deployment

```bash
# From local machine
cd /Users/carl/Documents/MobileCode/mobileGPS/deploy
./deploy-manual.sh 161.35.38.209 root

# On server
cd ~/gps-tracker
docker-compose pull
docker-compose up -d --build
docker-compose ps  # Check status
docker-compose logs -f backend  # View logs
```

---

## 🔐 Environment Variables

### Backend (.env file location: `gps-tracker/backend/.env`)

```bash
# Database
DATABASE_URL=postgresql://ble_user:PASSWORD@db:5432/ble_tracker

# JWT
SECRET_KEY=your-32-char-minimum-secret-key

# SendGrid Email
SENDGRID_API_KEY=SG.xxxxx
FROM_EMAIL=noreply@pinplot.me

# MZone API
MZONE_API_URL=https://api.myprofiler.com/oauth2/v1
MZONE_REDIRECT_URI=http://SERVER_IP/api/v1/mzone/callback
MZONE_CLIENT_ID=Tracking_GPS
MZONE_CLIENT_SECRET=secret-here

# Optional
DEBUG=False
```

### Docker Compose (.env file location: `gps-tracker/.env`)

```bash
POSTGRES_USER=ble_user
POSTGRES_PASSWORD=your-password
POSTGRES_DB=ble_tracker
MZONE_CLIENT_SECRET=secret-here
```

---

## 📡 API Endpoints

### Public Endpoints (No Auth Required)
```
POST   /register                 - Create new user
POST   /login                    - Get JWT token
POST   /send-verification-code   - Send email PIN
POST   /verify-pin              - Verify email with PIN
GET    /api/health              - Health check
```

### Protected Endpoints (Requires JWT)
```
# User Management
GET    /users/me                - Get current user
PUT    /users/me/email-alerts   - Toggle email alerts
DELETE /users/me                - Delete account

# BLE Tag/Tracker Management
POST   /tags/register           - Register new tracker
GET    /tags                    - List user's trackers
GET    /tags/{tag_id}           - Get tracker details
PUT    /tags/{tag_id}           - Update tracker
DELETE /tags/{tag_id}           - Remove tracker

# Location Updates (from trackers)
POST   /ble-location            - Receive location data

# Points of Interest (POI)
POST   /pois                    - Create POI
GET    /pois                    - List user's POIs
GET    /pois/{poi_id}           - Get POI details
PUT    /pois/{poi_id}           - Update POI
DELETE /pois/{poi_id}           - Delete POI

# POI-Tracker Linking (Geofencing)
POST   /poi-tracker-links       - Arm geofence
GET    /poi-tracker-links       - List armed geofences
DELETE /poi-tracker-links/{link_id} - Disarm geofence

# Alerts
GET    /geofence-alerts         - Get user's alerts
DELETE /geofence-alerts/{alert_id} - Dismiss alert

# MZone Integration
GET    /api/v1/mzone/authorize  - OAuth flow
GET    /api/v1/mzone/callback   - OAuth callback
POST   /api/v1/mzone/locations  - Get MZone data
```

---

## 🗄️ Database Schema

### Tables

**users**
- id (UUID, PK)
- email (unique)
- password_hash
- first_name, last_name, phone
- email_verified (boolean)
- email_alerts_enabled (boolean)
- is_active, is_admin
- created_at

**verification_pins**
- id (UUID, PK)
- email
- pin (6-digit code)
- expires_at
- created_at

**ble_tags** (GPS Trackers)
- id (UUID, PK)
- owner_id (FK to users)
- imei (unique identifier)
- device_name, device_model, description
- mac_address
- is_active
- last_seen, battery_level
- added_at

**pois** (Points of Interest)
- id (UUID, PK)
- user_id (FK to users)
- name, description
- address, postcode
- latitude, longitude
- radius (meters)
- created_at, updated_at

**poi_tracker_links** (Geofencing)
- id (UUID, PK)
- poi_id (FK to pois)
- tracker_id (FK to ble_tags)
- armed_at
- is_active

**geofence_alerts**
- id (UUID, PK)
- poi_tracker_link_id (FK)
- alert_type (entry/exit)
- distance (meters)
- triggered_at
- dismissed_at

---

## 🧪 Testing & Development

### Local Development

```bash
# Start all services
cd gps-tracker
docker-compose up -d

# Access services
Backend:  http://localhost:8000
Admin:    http://localhost:3000
Customer: http://localhost:3001
Flutter:  http://localhost:3002
Database: localhost:5432

# View logs
docker-compose logs -f backend
docker-compose logs -f admin

# Restart service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build backend
```

### Database Migrations

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
```

### Testing API

```bash
# Health check
curl http://localhost:8000/api/health

# Register user
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Login
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

---

## 🚨 Common Issues & Solutions

### Issue: Container won't start
```bash
# Check logs
docker-compose logs backend

# Check if port is in use
sudo lsof -i :8000

# Rebuild from scratch
docker-compose down
docker-compose up -d --build
```

### Issue: Database connection error
```bash
# Check database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Verify credentials in .env file
cat backend/.env | grep DATABASE_URL
```

### Issue: Changes not reflected
```bash
# For Python backend changes
docker-compose restart backend

# For Docker/requirements changes
docker-compose up -d --build backend

# For frontend changes (admin/customer)
docker-compose up -d --build admin
```

### Issue: SSL/Certificate errors
```bash
# Check certificate files exist
ls -la /etc/letsencrypt/live/pinplot.me/

# Renew certificate
sudo certbot renew

# Restart nginx
docker-compose restart nginx
```

---

## 📝 Code Patterns & Conventions

### Adding a New API Endpoint

1. **Define Pydantic models** (request/response schemas)
2. **Add endpoint in main.py**
3. **Use dependency injection** for database session
4. **Add authentication** if needed (Depends on decode_token)
5. **Handle errors** with HTTPException

Example:
```python
@app.post("/my-endpoint", response_model=MyResponse)
async def my_endpoint(
    request: MyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(decode_token)
):
    # Implementation
    return result
```

### Adding a Database Model

1. **Update models.py** with SQLAlchemy model
2. **Create migration**
   ```bash
   docker-compose exec backend alembic revision --autogenerate -m "add my_table"
   ```
3. **Review migration** in `alembic/versions/`
4. **Apply migration**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

### Adding a Service

1. **Create file** in `backend/app/services/my_service.py`
2. **Import in main.py** or other services
3. **Use for complex business logic** (email, external APIs, etc.)

---

## 🔒 Security Notes

### Removed Components
- **Redis** - Was defined but never used, exposed port 6379 publicly (security risk)

### Active Security Measures
- JWT authentication on all protected endpoints
- Password hashing with bcrypt
- SSL/TLS via Let's Encrypt
- Environment variables for secrets
- No hardcoded credentials

### Port Exposure
- **80, 443** - Public (HTTP/HTTPS)
- **8000** - Internal (backend API via nginx)
- **3000-3002** - Internal (dashboards via nginx)
- **5432** - Internal (PostgreSQL - NOT exposed publicly)

---

## 📞 Quick Commands Reference

```bash
# SERVER ACCESS
ssh root@161.35.38.209
cd ~/gps-tracker

# CONTAINER MANAGEMENT
docker ps                          # List running containers
docker-compose ps                  # List project containers
docker-compose logs -f backend     # Follow backend logs
docker-compose restart backend     # Restart service
docker-compose down                # Stop all
docker-compose up -d               # Start all (detached)
docker-compose up -d --build       # Rebuild and start

# DATABASE
docker-compose exec backend alembic upgrade head    # Run migrations
docker-compose exec db psql -U ble_user -d ble_tracker  # PostgreSQL CLI

# CLEANUP
docker system prune -a             # Clean unused images/containers
docker volume prune                # Clean unused volumes

# MONITORING
docker stats                       # Resource usage
docker-compose top                 # Process list
curl http://localhost:8000/api/health  # Health check
```

---

## 📚 Important Documentation Files

- `DEPLOYMENT.md` - Deployment procedures
- `GITHUB_SECRETS.md` - GitHub Actions secrets setup
- `PRODUCTION_CONFIG.md` - Production configuration
- `QUICK_REFERENCE.md` - Quick command reference
- `SENDGRID_SETUP.md` - Email configuration
- `EMAIL_VERIFICATION_README.md` - Email verification feature
- `GEOFENCE_MOCK_TESTING.md` - Geofencing testing
- `GETTING_STARTED.md` - Initial setup guide

---

**Remember:** Always test changes locally with `docker-compose` before deploying to production!
