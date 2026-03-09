# Production Secrets & Environment Configuration

## 📍 Where Your Secrets Live on Production

### Production Server: `root@161.35.38.209`

```
/root/gps-tracker/
├── .env                    # Root env file (for docker-compose)
│   ├── POSTGRES_USER
│   ├── POSTGRES_PASSWORD   ← PostgreSQL credentials
│   ├── POSTGRES_DB
│   └── MZONE_CLIENT_SECRET
│
└── backend/.env            # Backend env file (for FastAPI)
    ├── DATABASE_URL        ← Points to PostgreSQL
    ├── SECRET_KEY          ← JWT signing key
    ├── SENDGRID_API_KEY    ← Email service
    ├── FROM_EMAIL
    ├── MZONE_API_URL
    ├── MZONE_REDIRECT_URI
    ├── MZONE_CLIENT_ID
    ├── MZONE_CLIENT_SECRET
    ├── MZONE_USERNAME      ← GPS API credentials
    ├── MZONE_PASSWORD
    ├── MZONE_SCOPE
    ├── MZONE_GRANT_TYPE
    ├── MZONE_API_BASE
    ├── MZONE_VEHICLE_GROUP_ID
    └── DEBUG=False
```

## 🔒 How These Files Are Used

### 1. Root `.env` file
**Used by:** `docker-compose.yml`

```yaml
db:
  environment:
    POSTGRES_USER: ${POSTGRES_USER}      # ← From .env
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # ← From .env
    POSTGRES_DB: ${POSTGRES_DB}          # ← From .env
```

**Critical:** This file controls PostgreSQL database access!

### 2. Backend `backend/.env` file  
**Used by:** Backend FastAPI container

```yaml
backend:
  env_file:
    - ./backend/.env  # ← Loaded into container environment
```

**Contains:** All API keys, database connection string, JWT secrets

## 🛡️ Deployment Protection Analysis

### Current Workflows

#### ❌ `.github/workflows/deploy.yml` (Semi-Safe)

```yaml
# Step 1: Excludes .env from rsync ✅
rsync --exclude '.env' --exclude 'backend/.env' ...

# Step 2: Creates new .env files locally
cat > .env << 'ENVEOF'
  POSTGRES_PASSWORD=${POSTGRES_PASSWORD}  # From GitHub Secrets
ENVEOF

# Step 3: Uploads ONLY if files don't exist ✅ (after your fix)
ssh ... "test -f .env" || scp .env ...
```

**Status:** Safe NOW (with your fix), but still tries to manage secrets
**Risk:** GitHub Secrets might be incomplete/outdated

#### ✅ `.github/workflows/deploy-production.yml` (Completely Safe)

```yaml
# Step 1: Excludes .env from rsync ✅
rsync --exclude '.env' --exclude 'backend/.env' ...

# Step 2: Does docker-compose restart
docker-compose down --remove-orphans
docker-compose up -d

# That's it! Never touches .env files at all
```

**Status:** 100% Safe - Never touches secrets
**Risk:** None - purely code deployment

## ⚠️ What Could Break PostgreSQL

### Dangerous Scenarios:

1. **If .env gets overwritten with wrong password:**
   ```bash
   # PostgreSQL tries to start with wrong credentials
   POSTGRES_PASSWORD=wrong-password  # ← Database won't initialize!
   ```
   **Result:** Database container fails to start, app is down

2. **If backend/.env has wrong DATABASE_URL:**
   ```bash
   # Backend can't connect to database
   DATABASE_URL=postgresql://ble_user:wrong-pass@db:5432/ble_tracker
   ```
   **Result:** API returns 500 errors, no data access

3. **If .env files are deleted during deployment:**
   ```bash
   rsync --delete --no-exclude ...  # ← DANGEROUS!
   ```
   **Result:** All secrets lost, nothing works

## ✅ Current Protection Status

### What's Protected:

1. ✅ **rsync excludes .env files** (both workflows)
   ```bash
   --exclude '.env' --exclude 'backend/.env'
   ```

2. ✅ **deploy.yml only creates if missing** (your recent fix)
   ```bash
   test -f ~/gps-tracker/.env || scp .env ...
   ```

3. ✅ **deploy-production.yml never touches them**
   ```bash
   # No .env creation code at all
   ```

4. ✅ **postgres_data excluded from rsync**
   ```bash
   --exclude 'postgres_data'  # Database files never touched
   ```

## 🎯 Recommended Safe Setup

### Best Practice: Use `deploy-production.yml` only

**Why?**
- Never manages secrets
- Only syncs code files
- Restarts containers with existing config
- Zero risk of credential corruption

**Action Plan:**

```bash
# 1. Verify production .env files exist (do this once)
ssh root@161.35.38.209 "ls -la ~/gps-tracker/.env ~/gps-tracker/backend/.env"

# 2. If missing, create them manually (one-time setup)
ssh root@161.35.38.209
cd ~/gps-tracker
# Copy from .env.example and fill in real values
nano .env
nano backend/.env

# 3. Deploy code changes safely
git push origin main  # Triggers deploy-production.yml
```

### Alternative: Keep both workflows

If you want to keep `deploy.yml` as backup:
- It now has protection (only creates if missing)
- But GitHub Secrets might be incomplete
- Manual prod edits won't be reflected in GitHub Secrets

## 🔍 How to Verify Production Env Files

```bash
# Check if files exist
ssh root@161.35.38.209 "test -f ~/gps-tracker/.env && echo 'Root .env exists' || echo 'MISSING!'"
ssh root@161.35.38.209 "test -f ~/gps-tracker/backend/.env && echo 'Backend .env exists' || echo 'MISSING!'"

# Check PostgreSQL is using correct credentials
ssh root@161.35.38.209 "docker exec ble_tracker_db psql -U ble_user -d ble_tracker -c 'SELECT version();'"

# Check backend can connect to database
ssh root@161.35.38.209 "docker logs ble_tracker_backend | tail -20"
```

## 🚨 Emergency Recovery

If deployment breaks database connection:

```bash
# 1. SSH into production
ssh root@161.35.38.209

# 2. Check container status
docker ps -a | grep ble_tracker

# 3. Check PostgreSQL logs
docker logs ble_tracker_db

# 4. Verify .env files weren't corrupted
cat ~/gps-tracker/.env
cat ~/gps-tracker/backend/.env

# 5. Restart services
cd ~/gps-tracker
docker-compose down
docker-compose up -d

# 6. If database won't start, restore from backup
# (You do have database backups, right?)
```

## 📋 Deployment Safety Checklist

Before deploying:

- [ ] .env files exist on production
- [ ] PostgreSQL container is healthy
- [ ] Workflow excludes .env from rsync
- [ ] Workflow doesn't overwrite .env
- [ ] Database volume is excluded (postgres_data)
- [ ] Test deployment on non-production branch first

## Summary

**Current Status:** ✅ Your production secrets are SAFE

**Key Protection:**
1. Both workflows exclude .env files from rsync
2. deploy.yml now only creates if missing (not overwrites)
3. deploy-production.yml never touches .env at all
4. PostgreSQL data volume is never synced

**Recommendation:** Use `deploy-production.yml` for 100% safety

**PostgreSQL is protected because:**
- Root .env file is excluded from deployment
- postgres_data volume is excluded from rsync
- Existing credentials persist across deployments
- Database container uses mounted volume with existing data
