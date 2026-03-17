# Manual Deployment & Testing Guide

## ⚠️ IMPORTANT: Docker Containers Must Be RESTARTED

**Hot Reload is for Development Only.** When you make code changes and deploy:

1. ✅ Changes go into the Docker image during build
2. ✅ New image is created (different image hash)
3. ❌ **OLD CONTAINER** is still running the OLD image
4. ❌ **HOT RELOAD DOES NOT WORK** - you must restart/reboot the container

**Solution:** Containers must be stopped, removed, and new ones started with the NEW image.

---

## Manual Deployment Steps

### Step 1: SSH to Production Server

```bash
ssh ubuntu@161.35.38.209
# or
ssh user@your-server-ip
```

### Step 2: Verify Code Changes Are Committed

```bash
cd ~/beacon-telematics/gps-tracker
git status
# Should show: "nothing to commit, working tree clean"

git log --oneline -3
# Should show your latest commits
```

### Step 3: RESTART Containers (This is REQUIRED!)

```bash
cd ~/beacon-telematics/gps-tracker

# Option A: Full rebuild (SAFEST - clears all cache)
docker compose down
docker system prune -f --volumes
docker compose build --no-cache --pull
docker compose up -d

# Option B: Quick restart (faster, but might use cache)
docker compose restart

# Option C: Rebuild and restart (middle ground)
docker compose build --no-cache
docker compose up -d
```

**PICK ONE OF THE ABOVE BASED ON SITUATION:**
- **Option A**: Do this if changes still don't show (full nuclear option)
- **Option B**: Do this IF containers are already running latest image
- **Option C**: Do this when deploying code changes

### Step 4: Wait for Services to Start

```bash
# Check that containers are running
docker compose ps

# Should show all containers with status "Up"
# If any show "Exited" or "Restarting", there's an error
```

### Step 5: Verify Using Our Script

```bash
bash deploy/post-deploy-verify.sh
```

This will:
- ✅ Check containers are running
- ✅ Verify source code has expected changes
- ✅ Verify Docker image was rebuilt recently
- ✅ Check if app is responding
- ✅ Show what to expect in DevTools console

---

## Testing Changes in Browser

### Step 1: Open DevTools Console

1. Open app: https://beacontelematics.co.uk
2. Press **F12** (Windows/Linux) or **Cmd+Option+I** (Mac)
3. Go to **Console** tab
4. **Clear console** (⊘ button)

### Step 2: Navigate to Alerts Screen

Go to: https://beacontelematics.co.uk/#/alerts

### Step 3: Look for These Log Messages (in Console)

You should see something like:

```
🔄 AlertsScreen initialized - 7 day filter v1.0
📋 Loaded 45 alerts (total: 45, unread: 3)
✅ 7-day filter active: showing 12 recent alerts
🎨 Building alerts UI with 12 filtered alerts
⏰ Filtering to last 7 days: 45 total → 12 recent
```

**IF YOU DON'T SEE THESE LOGS:**
- Changes haven't been deployed
- Restart containers with: `docker compose down && docker compose build --no-cache --pull && docker compose up -d`

### Step 4: Verify UI

On the Alerts screen, you should see:

✅ **"Last 7 days"** label above the alerts list  
✅ **Only alerts from the past 7 days** are shown  
✅ Older alerts are filtered out  
✅ Pagination still works  

---

## Troubleshooting Checklist

### Problem: Changes Still Don't Show

**Root Causes (in order of likelihood):**

1. **Container not restarted** ← MOST COMMON
   ```bash
   docker compose down
   docker compose up -d
   ```

2. **Container using cached image**
   ```bash
   docker compose build --no-cache --pull
   docker compose up -d
   ```

3. **Browser cache**
   - Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - Or: Open DevTools → Settings → Disable cache (while DevTools open)

4. **Image wasn't rebuilt**
   ```bash
   # Full cleanup
   docker system prune -f --volumes
   docker compose build --no-cache --pull
   docker compose up -d
   ```

5. **Containers failed to start**
   ```bash
   docker compose logs flutter_web  # Check logs
   docker compose ps  # See status
   ```

### Problem: "Last 7 days" Label Appears But Filtering Doesn't Work

This means:
- ✅ Code IS deployed (label shows)
- ❌ Filter logic might have an error

Check:
1. Console for JavaScript errors (red text)
2. Backend logs: `docker compose logs backend`
3. Verify Alert objects have `createdAt` field

### Problem: No Logs Appear in Console

This means:
- ❌ New code is NOT running
- Restart containers and rebuild

---

## Post-Deployment Verification Script

Run this after restarting containers:

```bash
bash ~/beacon-telematics/gps-tracker/deploy/post-deploy-verify.sh
```

This checks:
- ✅ Containers are running
- ✅ Source code has changes
- ✅ Docker images are fresh
- ✅ App is responding
- ✅ No startup errors

---

## Container Restart Commands Reference

**Just restart (fast, might not pick up new code):**
```bash
docker compose restart beacon_telematics_flutter_web
```

**Rebuild without cache (recommended for code changes):**
```bash
docker compose build --no-cache beacon_telematics_flutter_web
docker compose up -d beacon_telematics_flutter_web
```

**Full nuclear rebuild (slowest but cleanest):**
```bash
cd ~/beacon-telematics/gps-tracker
docker compose down
docker system prune -f --volumes
docker rmi -f $(docker images --format '{{.Repository}}:{{.Tag}}' | grep beacon_telematics) 2>/dev/null || true
docker compose build --no-cache --pull
docker compose up -d
```

**Check container logs:**
```bash
docker logs -f beacon_telematics_flutter_web  # Follow logs in real-time
docker logs --tail 50 beacon_telematics_flutter_web  # Last 50 lines
```

---

## Why Hot Reload Doesn't Work in Production

| Aspect | Development | Production (Docker) |
|--------|-------------|-------------------|
| Code Change | `.dart` file saved | Code committed to Git |
| Build | Hot reload by IDE | Image built during deploy |
| Container | Single app instance | Container running old image |
| Update Method | Memory refresh (hot reload) | Rebuild + restart (cold start) |
| Result | Instant, seconds | Takes 2-5 minutes |

**Key Difference:** 
- Dev: Same process, hot reload updates it in memory
- Prod: New image built, old container still runs old image, must restart to use new image

---

## Expected Logs After Restart

When you refresh the Alerts page, you should see in DevTools Console:

```
🔄 AlertsScreen initialized - 7 day filter v1.0     ← Screen loaded
📋 Loaded 45 alerts (total: 45, unread: 3)          ← Data fetched from API
✅ 7-day filter active: showing 12 recent alerts    ← Filter applied
🎨 Building alerts UI with 12 filtered alerts       ← UI rendering
```

If you see these, the deploy is **SUCCESSFUL** ✅

If you DON'T see the🔄 line, something is wrong:
- Container possibly failed to restart
- Old image still running
- Clear cache and hard-refresh browser

---

## Summary

1. **Code changes → Git commit → Push**
2. **GitHub Actions builds new image**
3. **Containers must be RESTARTED to use new image**
4. **Hard refresh browser and check DevTools console for logs**
5. **Use the post-deploy-verify.sh script to validate**

**The most common reason changes don't show: Containers weren't restarted!**
