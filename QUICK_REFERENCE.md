# PinPlot Quick Reference

Quick commands for managing pinplot.me production server.

## 🔗 Access Points

```
Production:  https://pinplot.me
Server IP:   161.35.38.209
SSH:         ssh root@161.35.38.209
API Docs:    https://pinplot.me/api/docs
Admin:       https://pinplot.me/admin
```

## 🚀 Deployment

### Automatic (GitHub Actions)
```bash
cd /Users/carl/Documents/MobileCode/mobileGPS
git add .
git commit -m "Your changes"
git push origin main
# GitHub Actions automatically deploys
```

### Manual
```bash
cd /Users/carl/Documents/MobileCode/mobileGPS/deploy
./deploy-manual.sh 161.35.38.209 root
```

## 📊 Monitoring

### SSH to Server
```bash
ssh root@161.35.38.209
```

### Check All Services
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose ps'
```

### View Logs
```bash
# All logs
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs -f'

# Backend only
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs -f backend'

# Last 100 lines
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs --tail=100'
```

### Check Health
```bash
curl https://pinplot.me/api/health
curl -I https://pinplot.me
```

### Resource Usage
```bash
ssh root@161.35.38.209 'htop'
ssh root@161.35.38.209 'df -h'
ssh root@161.35.38.209 'docker stats --no-stream'
```

## 🔄 Service Management

### Restart All Services
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose restart'
```

### Restart Specific Service
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose restart backend'
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose restart nginx'
```

### Stop All Services
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose down'
```

### Start All Services
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose up -d'
```

### Rebuild and Restart
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose up -d --build'
```

## 🗄️ Database

### Backup Database
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose exec postgres pg_dump -U gpsuser gpsdb > backup_$(date +%Y%m%d_%H%M%S).sql'
```

### Download Backup
```bash
scp root@161.35.38.209:~/gps-tracker/backup_*.sql ./backups/
```

### Access Database
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose exec postgres psql -U gpsuser gpsdb'
```

### Check Database Size
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose exec postgres psql -U gpsuser gpsdb -c "SELECT pg_size_pretty(pg_database_size('"'"'gpsdb'"'"'));"'
```

## 🔐 SSL Certificate

### Check Certificate Status
```bash
ssh root@161.35.38.209 'sudo certbot certificates'
```

### Renew Certificate
```bash
ssh root@161.35.38.209 'sudo certbot renew'
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose restart nginx'
```

### Test Renewal
```bash
ssh root@161.35.38.209 'sudo certbot renew --dry-run'
```

## 📧 Email (SendGrid)

### Check Email Service
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs backend | grep "Email Service"'
```

### SendGrid Dashboard
```
https://app.sendgrid.com
Activity → Activity Feed (real-time email status)
Stats → Overview (email metrics)
```

## 🌐 DNS

### Check DNS Propagation
```bash
dig pinplot.me +short
nslookup pinplot.me
host pinplot.me
```

Should return: `161.35.38.209`

### Check All DNS Records
```bash
dig pinplot.me ANY
```

## 🔧 Mobile App

### Update Backend URL for Production

Edit: `gps-tracker/mobile-app/ble_tracker_app/lib/services/auth_service.dart`

```dart
static const String baseUrl = 'https://pinplot.me/api';
```

Edit: `gps-tracker/mobile-app/ble_tracker_app/lib/services/location_service.dart`

```dart
final String baseUrl = 'https://pinplot.me/api';
```

### Build Production APK
```bash
cd /Users/carl/Documents/MobileCode/mobileGPS/gps-tracker/mobile-app/ble_tracker_app
flutter clean
flutter pub get
flutter build apk --release
```

Output: `build/app/outputs/flutter-apk/app-release.apk`

## 🐛 Quick Troubleshooting

### Site Down
```bash
# Check if server responds
ping 161.35.38.209

# Check if services are running
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose ps'

# Check nginx logs
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs nginx'
```

### API Not Working
```bash
# Check backend logs
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs backend --tail=50'

# Restart backend
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose restart backend'
```

### Emails Not Sending
```bash
# Check email service configuration
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs backend | grep -i email'

# Check environment variables
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose exec backend env | grep SENDGRID'
```

### Database Issues
```bash
# Check database logs
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs postgres'

# Test connection
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose exec postgres psql -U gpsuser gpsdb -c "SELECT 1;"'
```

## 📁 Important Files on Server

```
~/gps-tracker/
├── docker-compose.yml          # Service orchestration
├── backend/.env               # Environment variables (SENSITIVE!)
├── nginx/nginx.conf          # Reverse proxy config
└── backups/                  # Database backups
```

## 🔑 GitHub Secrets

GitHub Repository → Settings → Secrets and variables → Actions

Required secrets:
- `DO_SERVER_IP` = `161.35.38.209`
- `DO_USER` = `root`
- `DO_SSH_PRIVATE_KEY` = (SSH private key)
- `SENDGRID_API_KEY` = (from SendGrid)
- `FROM_EMAIL` = `noreply@pinplot.me`
- `SECRET_KEY` = (generate with: `openssl rand -hex 32`)
- `DATABASE_URL` = `postgresql://gpsuser:PASSWORD@postgres:5432/gpsdb`
- `MZONE_CLIENT_ID`, `MZONE_CLIENT_SECRET`
- `MPROFILER_USERNAME`, `MPROFILER_PASSWORD`

## 📞 Quick Links

| Resource | URL |
|----------|-----|
| Production Site | https://pinplot.me |
| Admin Dashboard | https://pinplot.me/admin |
| API Docs | https://pinplot.me/api/docs |
| API Health | https://pinplot.me/api/health |
| SendGrid Dashboard | https://app.sendgrid.com |
| Digital Ocean Console | https://cloud.digitalocean.com |
| GitHub Repository | (your repo URL) |

## 💡 Pro Tips

1. **Always test locally first** before deploying to production
2. **Backup database before major updates**
3. **Monitor SendGrid usage** (free tier: 100 emails/day)
4. **Check logs after deployment** for any errors
5. **Use `--tail` flag** to limit log output
6. **Set up alerts** for server resource usage
7. **Keep secrets secure** - never commit `.env` files
8. **Document any manual changes** made on server

---

**Server**: 161.35.38.209  
**Domain**: pinplot.me  
**SSH**: `ssh root@161.35.38.209`
