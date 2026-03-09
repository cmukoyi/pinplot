# PinPlot - GPS Tracker Application

Real-time GPS tracking application with geofence alerts, email notifications, and multi-platform support.

🌐 **Production**: https://pinplot.me  
🖥️ **Server**: 161.35.38.209  
📧 **Email**: Powered by SendGrid  

## 🎯 Features

- ✅ **Real-time GPS Tracking** via MZone API integration
- ✅ **Geofence Alerts** with customizable zones (entry/exit notifications)
- ✅ **Email Notifications** for PIN verification and geofence events
- ✅ **Multi-platform Mobile App** (iOS, Android, Web)
- ✅ **Admin Dashboard** for system management
- ✅ **Customer Dashboard** for end users
- ✅ **Automatic Location Refresh** every 10 minutes
- ✅ **Custom Tracker Descriptions** synced from MZone API

## 📁 Project Structure

```
mobileGPS/
├── .github/workflows/          # CI/CD pipelines
├── deploy/                     # Deployment scripts
├── gps-tracker/
│   ├── backend/               # FastAPI backend
│   │   ├── app/
│   │   │   ├── services/      # Email, MZone, Geofence services
│   │   │   ├── models.py      # Database models
│   │   │   └── main.py        # API endpoints
│   │   ├── alembic/           # Database migrations
│   │   └── requirements.txt
│   ├── admin-dashboard/       # Admin UI (Node.js + Express)
│   ├── customer-dashboard/    # Customer UI (Node.js + Express)
│   ├── mobile-app/            # Flutter mobile app
│   │   └── ble_tracker_app/
│   └── nginx/                 # Reverse proxy configuration
├── DEPLOYMENT.md              # General deployment guide
├── PRODUCTION_CONFIG.md       # PinPlot-specific production config
├── SENDGRID_SETUP.md         # Email service setup guide
└── README.md                  # This file
```

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd mobileGPS
```

2. **Configure environment variables**
```bash
cd gps-tracker/backend
cp .env.example .env
# Edit .env with your credentials
```

3. **Start services with Docker**
```bash
cd gps-tracker
docker-compose up -d
```

4. **Access services**
- Backend API: http://localhost:5001/docs
- Admin Dashboard: http://localhost:3000
- Customer Dashboard: http://localhost:3001
- MailHog (email testing): http://localhost:8025

### Production Deployment

Full production deployment guide for **pinplot.me** (161.35.38.209):

📖 **See**: [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md)

Quick deploy:
```bash
cd deploy
./deploy-manual.sh 161.35.38.209 root
```

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15
- **Email**: SendGrid API (Free tier: 100 emails/day)
- **Authentication**: JWT tokens with email verification
- **Integrations**: MZone API, MProfiler API

### Frontend
- **Admin Dashboard**: Node.js + Express + HTML/CSS
- **Customer Dashboard**: Node.js + Express + HTML/CSS
- **Mobile App**: Flutter 3.x (iOS, Android, Web)

### Infrastructure
- **Deployment**: Digital Ocean Ubuntu 22.04
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Reverse Proxy**: Nginx
- **SSL**: Let's Encrypt

## 📱 Mobile App

### Development
```bash
cd gps-tracker/mobile-app/ble_tracker_app
flutter pub get
flutter run
```

### Build for Production
```bash
# Android
flutter build apk --release

# iOS
flutter build ios --release

# Web
flutter build web
```

### Configuration

Update backend URL in `lib/services/auth_service.dart`:
```dart
// Development
static const String baseUrl = 'http://192.168.0.10:5001';

// Production
static const String baseUrl = 'https://pinplot.me/api';
```

## 📧 Email Notifications

The system sends emails for:
- **Verification PINs** - 6-digit codes for user registration
- **Welcome Emails** - After successful account verification
- **Geofence Alerts** - When tracker enters/exits geofenced areas

**Email Provider**: SendGrid (Free tier: 100 emails/day)  
**Setup Guide**: [SENDGRID_SETUP.md](SENDGRID_SETUP.md)

## 🗄️ Database Schema

Key tables:
- `users` - User accounts with email verification
- `ble_tags` - GPS trackers (IMEI, description, device_name)
- `pois` - Points of Interest (geofence zones)
- `geofence_alerts` - Alert history for geofence events

Migrations managed with Alembic:
```bash
cd gps-tracker/backend
alembic upgrade head
```

## 🔐 Environment Variables

### Required for Production

```bash
# Application
DEBUG=False
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Database
DATABASE_URL=postgresql://gpsuser:password@postgres:5432/gpsdb

# Email (SendGrid)
SENDGRID_API_KEY=SG.your-api-key-here
FROM_EMAIL=noreply@pinplot.me

# MZone API
MZONE_CLIENT_ID=your-client-id
MZONE_CLIENT_SECRET=your-client-secret

# MProfiler API
MPROFILER_USERNAME=your-username
MPROFILER_PASSWORD=your-password
```

See [.env.example](.env.example) for complete list.

## 🚦 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/verify` - Verify email with PIN
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/resend-pin` - Resend verification PIN

### Vehicles
- `GET /api/vehicles` - Get all tracked vehicles
- `POST /api/tags/add` - Add new tracker

### Geofencing
- `GET /api/pois` - List all POIs
- `POST /api/pois` - Create new POI
- `POST /api/pois/{poi_id}/arm` - Arm geofence
- `POST /api/pois/{poi_id}/disarm` - Disarm geofence

**Full API Documentation**: https://pinplot.me/api/docs

## 🔄 Automatic Features

- **Location Refresh**: Every 10 minutes on map screen
- **Geofence Monitoring**: Continuous checking when geofences are armed
- **Description Sync**: Auto-sync tracker descriptions from MZone API
- **Email Alerts**: Instant notifications for geofence events

## 📊 Monitoring

### Health Checks
```bash
# Backend health
curl https://pinplot.me/api/health

# Database connection
ssh root@161.35.38.209 'cd ~/gps-tracker/gps-tracker && docker-compose exec postgres psql -U gpsuser -c "SELECT 1;"'
```

### Logs
```bash
# SSH to server
ssh root@161.35.38.209

# View logs
cd ~/gps-tracker/gps-tracker
docker-compose logs -f backend
docker-compose logs -f admin-dashboard
docker-compose logs -f customer-dashboard
```

### Email Analytics
- SendGrid Dashboard: https://app.sendgrid.com
- Activity Feed for real-time email tracking

## 🐛 Troubleshooting

### Common Issues

**Emails not sending**
- Check SendGrid API key is configured
- Verify sender email in SendGrid dashboard
- Check backend logs: `docker-compose logs backend | grep "Email"`

**Location not loading**
- Verify MZone OAuth credentials
- Check backend logs for OAuth errors
- Ensure tracker IMEI is correct

**Geofence alerts not triggering**
- Ensure geofence is armed
- Check user has email alerts enabled
- Verify tracker is inside/outside geofence area

See [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md) for detailed troubleshooting.

## 📚 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - General deployment guide
- [PRODUCTION_CONFIG.md](PRODUCTION_CONFIG.md) - PinPlot production setup
- [SENDGRID_SETUP.md](SENDGRID_SETUP.md) - Email service configuration
- [gps-tracker/GETTING_STARTED.md](gps-tracker/GETTING_STARTED.md) - Development setup
- [gps-tracker/EMAIL_VERIFICATION_README.md](gps-tracker/EMAIL_VERIFICATION_README.md) - Email verification flow

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test locally
3. Commit: `git commit -m "Add my feature"`
4. Push: `git push origin feature/my-feature`
5. Create Pull Request

## 📝 License

Proprietary - All rights reserved

## 🔗 Links

- **Production Site**: https://pinplot.me
- **Server IP**: 161.35.38.209
- **API Docs**: https://pinplot.me/api/docs
- **SendGrid**: https://app.sendgrid.com
- **Digital Ocean**: https://cloud.digitalocean.com

## 📞 Support

- Check documentation in this repository
- Review troubleshooting guides
- Check server logs for detailed errors

---

**Version**: 1.0.0  
**Last Updated**: March 3, 2026  
**Production URL**: https://pinplot.me  
**Server**: 161.35.38.209
