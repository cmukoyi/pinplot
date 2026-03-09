# Geofence State Tracking System

## Overview

The geofence alerting system now uses explicit state tracking to prevent duplicate alerts. Alerts are **only** generated when a tracker's state changes relative to a geofence (INSIDE ↔ OUTSIDE).

## Key Features

### 1. **State-Based Alert Generation**

Each POI-tracker link (POITrackerLink) now maintains:
- `last_known_state`: The last observed state (`unknown`, `inside`, or `outside`)
- `last_state_check`: Timestamp of the last position check

### 2. **State Transition Logic**

Alerts are generated **only** when state changes occur:

| Previous State | Current State | Alert Generated | Event Type | Message Format |
|---------------|---------------|-----------------|------------|----------------|
| UNKNOWN | INSIDE | ✅ Yes | ENTRY | "Tracker XXX is inside YYY Location" |
| UNKNOWN | OUTSIDE | ✅ Yes | EXIT | "Tracker XXX is outside YYY Location" |
| INSIDE | OUTSIDE | ✅ Yes | EXIT | "Tracker XXX is outside YYY Location" |
| OUTSIDE | INSIDE | ✅ Yes | ENTRY | "Tracker XXX is inside YYY Location" |
| INSIDE | INSIDE | ❌ No | - | State unchanged, no alert |
| OUTSIDE | OUTSIDE | ❌ No | - | State unchanged, no alert |

### 3. **Preventing Alert Spam**

**Problem:** Without state tracking, every position update outside a geofence would trigger a new "EXIT" alert, flooding users with duplicate notifications.

**Solution:** The system tracks the last known state. If a tracker is already outside and receives another position update that's still outside, no alert is generated. The next alert only fires when the tracker re-enters the geofence (state change: OUTSIDE → INSIDE).

**Example Scenario:**
```
Time 10:00 - Tracker is INSIDE "Home" geofence (initial state: UNKNOWN → INSIDE)
  ✅ Alert: "Tracker Car is inside Home"
  
Time 10:15 - Tracker moves OUTSIDE "Home" (state change: INSIDE → OUTSIDE)
  ✅ Alert: "Tracker Car is outside Home"
  
Time 10:30 - Tracker still OUTSIDE "Home" (no state change: OUTSIDE → OUTSIDE)
  ❌ No alert (already outside)
  
Time 10:45 - Tracker still OUTSIDE "Home" (no state change: OUTSIDE → OUTSIDE)
  ❌ No alert (already outside)
  
Time 11:00 - Tracker moves INSIDE "Home" (state change: OUTSIDE → INSIDE)
  ✅ Alert: "Tracker Car is inside Home"
```

## Database Schema

### GeofenceState Enum
```python
class GeofenceState(enum.Enum):
    UNKNOWN = "unknown"  # Initial state before first check
    INSIDE = "inside"    # Tracker is within geofence radius
    OUTSIDE = "outside"  # Tracker is outside geofence radius
```

### POITrackerLink Model Changes
```sql
ALTER TABLE poi_tracker_links 
ADD COLUMN last_known_state geofence_state DEFAULT 'unknown' NOT NULL;

ALTER TABLE poi_tracker_links 
ADD COLUMN last_state_check TIMESTAMP WITH TIME ZONE;
```

## Alert Message Format

### Single POI (Geofence)
- **Entry:** "Tracker [name] is inside [POI name]"
- **Exit:** "Tracker [name] is outside [POI name]"

### Route POI (Delivery)
- **Origin Exit:** "Tracker [name] left origin ([route name])"
- **Destination Entry:** "Tracker [name] arrived at destination ([route name])"

## Tracker Name Priority

The system uses a priority order to determine the tracker display name:
1. **Description** (if set by user)
2. **Device Name** (from MZone API)
3. **IMEI Last 4 Digits** (e.g., "GPS Tracker (1234)")
4. **Generic** (fallback: "GPS Tracker")

## Email Notifications

Users with `email_alerts_enabled = true` receive email notifications for each alert:

**Subject:** `🟢 Alert: Tracker [name] is inside [location]`  
**Subject:** `🔴 Alert: Tracker [name] is outside [location]`

**Email Content:**
- Tracker name
- Status (inside/outside location)
- POI name
- Coordinates
- Timestamp
- Google Maps link

## API Response Format

### GET `/api/v1/alerts`

Returns alert list with formatted data:
```json
{
  "alerts": [
    {
      "id": "uuid",
      "poi_id": "uuid",
      "tracker_id": "uuid",
      "user_id": "uuid",
      "event_type": "entry",  // or "exit"
      "latitude": 40.7128,
      "longitude": -74.0060,
      "is_read": false,
      "created_at": "2026-03-08T10:00:00Z",
      "poi_name": "Home",
      "tracker_name": "Car GPS"
    }
  ],
  "total": 25,
  "unread_count": 5
}
```

**Client-side formatting:**
- `event_type = "entry"` → Display: "Tracker {tracker_name} is inside {poi_name}"
- `event_type = "exit"` → Display: "Tracker {tracker_name} is outside {poi_name}"

## Implementation Details

### GeofenceService._check_single_poi()

1. **Query POITrackerLink** to get `last_known_state`
2. **Check current position** against geofence coordinates/radius
3. **Determine current state** (INSIDE or OUTSIDE)
4. **Compare states:**
   - If `last_known_state == UNKNOWN`: Generate alert with current state
   - If state changed (INSIDE↔OUTSIDE): Generate alert
   - If state unchanged: Skip alert
5. **Update link** with new `last_known_state` and `last_state_check`
6. **Send email** if user has email alerts enabled

### Position Check Flow

```
1. User's tracker sends position update to backend
   ↓
2. Backend calls GeofenceService.check_geofences_for_tracker()
   ↓
3. For each ARMED POI linked to this tracker:
   a. Get POITrackerLink (includes last_known_state)
   b. Calculate distance from tracker to POI center
   c. Determine: is_inside = (distance <= radius)?
   d. Compare with last_known_state
   e. If state changed → Create GeofenceAlert, send email
   f. Update last_known_state = current_state
   ↓
4. Return list of generated alerts
```

## Migration Instructions

### Running the Migration

```bash
cd gps-tracker/backend
alembic upgrade head
```

This will execute migration `006_add_geofence_state_tracking.py`, which:
1. Creates `geofence_state` enum type
2. Adds `last_known_state` column (default: 'unknown')
3. Adds `last_state_check` timestamp column

### Rollback (if needed)

```bash
alembic downgrade -1
```

## Testing the Feature

### Test Scenario 1: Initial State Detection

1. **Create a POI** named "Office" at lat/lon with 150m radius
2. **ARM the POI** for a tracker IMEI
3. **Send position update** that is INSIDE the geofence
4. **Expected Result:** 
   - Alert created: "Tracker XXX is inside Office"
   - Email sent (if enabled)
   - `last_known_state` = INSIDE

### Test Scenario 2: Exit Detection

1. **Tracker is INSIDE** "Office" (last_known_state = INSIDE)
2. **Send position update** that is OUTSIDE the geofence
3. **Expected Result:**
   - Alert created: "Tracker XXX is outside Office"
   - Email sent (if enabled)
   - `last_known_state` = OUTSIDE

### Test Scenario 3: Duplicate Prevention

1. **Tracker is OUTSIDE** "Office" (last_known_state = OUTSIDE)
2. **Send position update** that is still OUTSIDE
3. **Expected Result:**
   - ❌ **No alert created** (state unchanged)
   - ❌ **No email sent**
   - `last_known_state` remains OUTSIDE
   - `last_state_check` updated with current timestamp

### Test Scenario 4: Re-entry Detection

1. **Tracker is OUTSIDE** "Office" (last_known_state = OUTSIDE)
2. **Send position update** that is INSIDE the geofence
3. **Expected Result:**
   - Alert created: "Tracker XXX is inside Office"
   - Email sent (if enabled)
   - `last_known_state` = INSIDE

## Logging

The service logs all state transitions:

```python
logger.info(f"Initial state for Office, tracker ABC123: inside")
logger.info(f"State change for Office, tracker ABC123: INSIDE → OUTSIDE")
logger.info(f"State change for Office, tracker ABC123: OUTSIDE → INSIDE")
logger.debug(f"No state change for Office, tracker ABC123: outside")
```

## Performance Considerations

- **State checks are efficient:** Single database query per POI-tracker link
- **No alert table queries:** State is stored directly in POITrackerLink, avoiding expensive ORDER BY queries on GeofenceAlert table
- **Last_state_check timestamp:** Can be used to identify stale trackers (no updates in X hours)

## Future Enhancements

1. **Dwell Time Alerts:** Alert only if tracker remains outside for X minutes
2. **Alert Cooldown:** Minimum time between alerts per POI-tracker combo
3. **State History:** Track state transitions over time for analytics
4. **Multi-State Support:** Add "APPROACHING" state for trackers near geofence boundary

---

## Code Files Modified

1. **Backend Models:**
   - `app/models.py` - Added GeofenceState enum, updated POITrackerLink
   
2. **Backend Services:**
   - `app/services/geofence_service.py` - Refactored state tracking logic
   - `app/services/email_service.py` - Updated alert email format
   
3. **Backend API:**
   - `app/main.py` - Updated alerts endpoint to use proper tracker naming
   
4. **Database:**
   - `alembic/versions/006_add_geofence_state_tracking.py` - Migration script

## References

- Haversine Formula: Used for distance calculation between coordinates
- State Machine Pattern: Implements state transitions (UNKNOWN → INSIDE/OUTSIDE ↔ INSIDE/OUTSIDE)
