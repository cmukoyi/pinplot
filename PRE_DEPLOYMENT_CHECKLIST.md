# 🚀 BeaconTelematics Pre-Deployment Checklist

**REQUIRED: Complete this BEFORE pushing to `main` branch**

---

## ✅ Configuration Validation (CRITICAL)

**These three rules MUST be followed or production breaks:**

### Rule 1: Nginx Port Mappings ⚠️ CRITICAL

**Location:** `gps-tracker/docker-compose.yml` lines ~88-89

**MUST BE:**
```yaml
nginx:
  image: nginx:alpine
  container_name: beacon_telematics_nginx
  ports:
    - 80:80     ✅ CORRECT
    - 443:443   ✅ CORRECT
```

**NEVER CHANGE TO:**
```yaml
  ports:
    - 8080:80   ❌ BREAKS PRODUCTION
    - 8443:443  ❌ BLOCKS EXTERNAL USERS
```

**Why:** Firewall rules allow ports 80/443 only. If you change to 8080/8443, nobody outside the server can reach the site.

**Check Before Committing:**
```bash
grep -A 3 "nginx:" gps-tracker/docker-compose.yml | grep "ports:" -A 2
# Should show:
#   - 80:80
#   - 443:443
```

---

### Rule 2: Database Name ⚠️ CRITICAL

**Location:** `gps-tracker/docker-compose.yml` lines ~6-8

**MUST BE:**
```yaml
db:
  environment:
    POSTGRES_DB: beacon_telematics  ✅ CORRECT (matches backend)
```

**NEVER CHANGE TO:**
```yaml
    POSTGRES_DB: beacon_user        ❌ BREAKS ALL API CALLS
```

**Why:** Backend looks for database named `beacon_telematics`. If you change it, backend cannot connect and all API calls fail.

**Check Before Committing:**
```bash
grep "POSTGRES_DB" gps-tracker/docker-compose.yml
# Should show: POSTGRES_DB: beacon_telematics
```

---

### Rule 3: Backend Database URL ⚠️ CRITICAL

**Location:** `gps-tracker/backend/.env`

**MUST BE:**
```
DATABASE_URL=postgresql://beacon_user:PASSWORD@db:5432/beacon_telematics
                                                   ^^MUST BE beacon_telematics
```

**NEVER CHANGE TO:**
```
DATABASE_URL=postgresql://beacon_user:PASSWORD@db:5432/beacon_user
                                                   ^^WRONG - backend won't connect
```

**Check Before Committing:**
```bash
grep DATABASE_URL gps-tracker/backend/.env | grep beacon_telematics
# Should show DATABASE_URL with beacon_telematics at the end
```

---

## 🔒 Pre-Commit Validation Script

**Run this BEFORE committing any changes:**

```bash
cd gps-tracker/deploy
bash validate-deployment.sh
```

**Expected Output:**
```
✅ docker-compose.yml: nginx exposed on 80:80 and 443:443
✅ Firewall: Port 80 is OPEN
✅ Firewall: Port 443 is OPEN
✅ Documentation: Ports correctly documented as 80/443
✅ SSL Certificate: Valid until [DATE]

========================================
✅ All validation checks PASSED
Safe to proceed with deployment
========================================
```

**If you see ❌ errors:** DO NOT PUSH. Fix the issue first.

---

## 📋 Full Deployment Checklist

Before running `git push origin main`:

### Code Changes
- [ ] Changes tested locally
- [ ] Database migrations tested (`alembic upgrade head` locally)
- [ ] No `.env` or sensitive files committed
- [ ] Commit messages are clear and descriptive

### Configuration Validation
- [ ] Ran `bash deploy/validate-deployment.sh` ✅ PASSED
- [ ] Verified nginx ports: 80:80 and 443:443 (not 8080:8443)
- [ ] Verified database name: beacon_telematics (not beacon_user)
- [ ] Verified backend DATABASE_URL ends with beacon_telematics
- [ ] Checked DEPLOYMENT_STRATEGY.md matches your changes

### Pre-Push Checks
```bash
# 1. Validate configuration
cd gps-tracker/deploy && bash validate-deployment.sh

# 2. Check docker-compose syntax
docker-compose config > /dev/null && echo "✅ Valid"

# 3. View changes before pushing
git diff gps-tracker/docker-compose.yml   # Check for port changes
git diff gps-tracker/backend/.env         # Check for DB name changes
git status                                 # Check what will be pushed

# 4. Final confirmation
echo "Pushing to main. Automated deployment will start in 30 seconds..."
```

- [ ] All checks passed
- [ ] Ready to deploy to production

### After Push (Automated)

The GitHub Actions workflow will:
1. Back up database ✅
2. Run migrations ✅
3. Deploy new code ✅
4. Run health checks ✅
5. Deploy completes in ~2 minutes

**Monitor here:** https://github.com/cmukoyi/beaconTelematics/actions

---

## 🚨 If Something Goes Wrong

**Site is down / unreachable after deployment:**

```bash
# SSH to server immediately
ssh root@161.35.38.209

# Check what went wrong
cd /root/beacon-telematics/gps-tracker
docker compose logs --tail=50 backend
docker compose logs --tail=50 nginx
docker compose logs --tail=50 db

# Run rollback if needed
bash deploy/rollback.sh
# Answer: yes

# You now have the previous working state restored
```

---

## 🔍 Critical Config History

These commits broke production - NEVER repeat:

| Commit | What Broke | Impact | Fix |
|--------|-----------|--------|-----|
| 5abbde8 | Reverted nginx ports to 8080:8443 | 100% site downtime | Commit ea6b04d |
| (hypothetical) | Changed POSTGRES_DB to beacon_user | All API calls fail | Revert + restart |
| (hypothetical) | Changed backend DATABASE_URL | Backend can't connect | Fix .env |

---

## ✨ Quick Reference

**The 3 Things That Must Never Change:**

```
1. nginx ports → ALWAYS 80:80 and 443:443
2. Database name → ALWAYS beacon_telematics
3. Backend DATABASE_URL → ALWAYS ends with /beacon_telematics
```

**Before every deployment run:**
```bash
bash gps-tracker/deploy/validate-deployment.sh
```

**If validation fails:**
```
DO NOT PUSH
Fix the issue first
Run validation again until ✅ PASSED
```

---

## 👥 Sharing This Checklist

**Post in team Slack/chat before every deployment:**

```
🚀 DEPLOYMENT ABOUT TO START

Please verify:
1. Run: bash gps-tracker/deploy/validate-deployment.sh ✅ ?
2. Check README: https://github.com/cmukoyi/beaconTelematics/blob/main/PRE_DEPLOYMENT_CHECKLIST.md
3. Confirm no port/database config changes made
4. Confirm no .env secrets committed

Starting deployment in 5 minutes...
```

---

## 📝 Deployment Record

After successful deployment, update this:

| Date | Deployed By | Changes | Status |
|------|-------------|---------|--------|
| 2026-03-17 | (Your name) | Fix: nginx ports 80/443 | ✅ LIVE |
| | | | |

---

**Last Updated:** March 17, 2026  
**Created By:** Development Team  
**Review Frequency:** Before every deployment
