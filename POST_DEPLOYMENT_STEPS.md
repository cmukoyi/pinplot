# Post-Deployment Steps

Quick reference for rebuilding and restarting Docker containers after deployment to see changes on production.

## 🚀 Quick Deploy & Rebuild

### One-Liner (Recommended)
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose up -d --build && docker-compose ps'
```

### Step-by-Step

```bash
# 1. SSH to production server
ssh root@161.35.38.209

# 2. Navigate to project directory
cd ~/gps-tracker

# 3. Pull latest changes (if manual deployment)
git pull origin main

# 4. Rebuild and restart all containers
docker-compose up -d --build

# 5. Check container status
docker-compose ps

# 6. Watch logs for errors (Ctrl+C to exit)
docker-compose logs -f --tail=50
```

## 🎯 Rebuild Specific Services

### Flutter Web App Only
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose up -d --build ble_tracker_flutter_web'
```

### Backend API Only
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose up -d --build backend'
```

### Nginx Only
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose restart nginx'
```

## ✅ Verify Changes Are Live

1. **Open production site**: https://pinplot.me

2. **Hard refresh browser** (clear cache):
   - Mac: `Cmd + Shift + R`
   - Windows/Linux: `Ctrl + Shift + R`

3. **Test recent changes**:
   - Avatar menu shows email ✓
   - Settings shows "Location Alerts" ✓
   - Settings shows "Refresh GPS Positions" ✓
   - Create Locations shows "From | To" ✓

4. **Check browser console** for errors:
   - Right-click → Inspect → Console tab

## 🔍 Troubleshooting

### 502 Bad Gateway (Flutter Web Container Down)

```bash
# Quick fix: Restart with last working images (don't rebuild)
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose down && docker-compose up -d'

# Verify containers running
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose ps'

# If still failing, check Flutter build logs
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs ble_tracker_flutter_web --tail=200'
```

This restores the last successfully built version without attempting to rebuild.

### Changes Not Showing Up

```bash
# View Flutter web build logs
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs ble_tracker_flutter_web --tail=100'

# Force rebuild with no cache
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose build --no-cache ble_tracker_flutter_web && docker-compose up -d'
```

### Backend Changes Not Working

```bash
# Check backend logs
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs backend --tail=100'

# Restart backend
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose restart backend'
```

### All Services Down

```bash
# Check all container status
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose ps'

# Restart everything
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose down && docker-compose up -d'
```

## 📊 Monitor Deployment

### Watch Real-Time Logs
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose logs -f'
```

### Check Resource Usage
```bash
ssh root@161.35.38.209 'docker stats --no-stream'
```

### Verify All Services Running
```bash
ssh root@161.35.38.209 'cd ~/gps-tracker && docker-compose ps'
```

Expected output: All services should show "Up" status

## 📝 Notes

- **GitHub Actions**: Automatically deploys on push to `main` branch
- **Manual rebuild**: Use commands above if automatic deployment needs immediate refresh
- **Browser caching**: Always hard refresh to see latest changes
- **Build time**: Flutter web build takes ~2-3 minutes
- **Zero downtime**: `docker-compose up -d --build` updates without stopping services

---

**Production**: https://pinplot.me  
**Server**: 161.35.38.209  
**SSH**: `ssh root@161.35.38.209`
