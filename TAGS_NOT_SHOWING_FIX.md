# Critical Fix: Tags Not Showing Issue

## Problem
After commit `55ab238`, tags stopped displaying in the Create Location dropdown.

## Root Cause
The frontend code was updated to use `tag['description']` instead of `tag['device_name']`, BUT the database was missing the `description` column in the `ble_tags` table!

**Timeline:**
1. Models.py had `description` field defined
2. Backend API tried to return `tag.description`  
3. Database table `ble_tags` did NOT have a `description` column
4. SQLAlchemy failed to load or returned errors
5. Frontend received no tags or malformed data

## What Was Missing
The `ble_tags` table was created in migration `001` without the `description` column. No subsequent migration added it, even though the model definition included it.

## The Fix

### Migration Created (007)
File: `gps-tracker/backend/alembic/versions/007_add_description_to_ble_tags.py`

Adds:
```sql
ALTER TABLE ble_tags ADD COLUMN description VARCHAR(255);
```

### Deployment Steps Required

**After GitHub Actions completes deployment (commit 0078dda):**

1. **SSH to production server:**
   ```bash
   ssh root@161.35.38.209
   ```

2. **Navigate to gps-tracker:**
   ```bash
   cd ~/gps-tracker
   ```

3. **Run ALL pending migrations (006 and 007):**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

4. **Verify migrations applied:**
   ```bash
docker-compose exec backend alembic current
   ```
   
   Should show: `revision: 007`

5. **Verify column exists:**
   ```bash
   docker-compose exec postgres psql -U gpsuser -d gpsdb -c "\d ble_tags"
   ```
   
   Should show `description | character varying(255)` in the column list

6. **Restart backend (if needed):**
   ```bash
   docker-compose restart backend
   ```

7. **Test the app:**
   - Open mobile app in browser
   - Go to Settings → Create Location
   - Dropdown should now show tags correctly
   - Toggle "Display IMEI" should work

## What Gets Fixed
✅ Tags will display in Create Location dropdown  
✅ Description field will be NULL for existing tags (shows fallback to device_name → imei)  
✅ New tags from MZone API will have description populated  
✅ Frontend priority logic works: description → device_name → imei

## Commits
- `55ab238` - Frontend change to use description field
- `0078dda` - Migration 007 to add description column

## Prevention
**Lesson learned:** When updating frontend code to use a new backend field:
1. Always verify the database migration exists
2. Check that the column is in the database schema
3. Test migrations locally before deploying
4. Run migrations on staging/production before deploying code changes

## Status
- ✅ Migration created
- ✅ Commits pushed to GitHub  
- 🔄 GitHub Actions deploying (in progress)
- ⏳ Migration needs to run on production
- ⏳ Testing required after migration

## Next Actions
1. Wait for GitHub Actions to complete
2. SSH to production and run migrations
3. Test that tags display correctly
4. Verify description field works with MZone API data
