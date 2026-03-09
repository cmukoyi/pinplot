# Geofence Notification Mock Testing

## Overview

This document explains how to test the geofence notification system using mock location data.

## Database Persistence: ✅ CONFIRMED

**Yes, the app persists geofences in the database with their locations:**

1. **POIs Table** - Stores all geofence locations:
   - `id`, `name`, `poi_type` (single or route)
   - `latitude`, `longitude`, `radius` (origin location)
   - `destination_latitude`, `destination_longitude`, `destination_radius` (for routes)
   - `address`, `destination_address`
   - `is_active`, `user_id`

2. **GeofenceAlerts Table** - Stores all notification history:
   - `id`, `poi_id`, `tracker_id`, `user_id`
   - `event_type` (ENTRY or EXIT)
   - `latitude`, `longitude` (where the event occurred)
   - `is_read`, `created_at`

All data persists across app restarts in PostgreSQL.

## Mock Test Endpoint

The backend now includes a test endpoint: **POST /api/v1/test/mock-location**

This endpoint simulates a tracker location update to test geofence alerts and email notifications.

### Endpoint Details

- **URL**: `http://localhost:8000/api/v1/test/mock-location`
- **Method**: POST
- **Auth**: Bearer token required
- **Body**:
  ```json
  {
    "tracker_id": "647b512f-92b8-4184-8a82-4321365d6336",
    "latitude": 51.385,
    "longitude": -0.205
  }
  ```

### Response

```json
{
  "success": true,
  "tracker_id": "647b512f-92b8-4184-8a82-4321365d6336",
  "test_location": {
    "latitude": 51.385,
    "longitude": -0.205
  },
  "alerts_triggered": 1,
  "email_alerts_enabled": true,
  "message": "Test completed. 1 alert(s) generated. Email notifications sent.",
  "alerts": [
    {
      "alert_id": "uuid",
      "poi_id": "uuid",
      "poi_name": "Laptop Delivery",
      "poi_type": "single",
      "event_type": "EXIT",
      "latitude": 51.385,
      "longitude": -0.205,
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "mailhog_url": "http://localhost:8025",
  "instructions": "Check MailHog at http://localhost:8025 to see email notifications..."
}
```

## Test Scenarios

### Current Armed POIs

Based on the database, we have these POIs armed to tracker `647b512f-92b8-4184-8a82-4321365d6336`:

1. **"Laptop Delivery"** (single POI)
   - Location: 51.375896, -0.194597
   - Radius: 150m
   
2. **"Test Delivery"** (route POI)
   - Origin: 51.375896, -0.194597 (radius: 150m)
   - Destination: 51.388925, -0.185216 (radius: 150m)

### Test Case 1: Exit FROM Address (Outside Geofence)

Simulate tracker leaving the origin:

```bash
# First, login to get token
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' \
  | jq -r '.access_token'

# Use the token in the next request
export TOKEN="your_token_here"

# Test location OUTSIDE geofence (1km away)
curl -X POST http://localhost:8000/api/v1/test/mock-location \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "tracker_id": "647b512f-92b8-4184-8a82-4321365d6336",
    "latitude": 51.385,
    "longitude": -0.205
  }' | jq
```

**Expected Result:**
- EXIT event triggered for both POIs
- Email sent to MailHog
- Alert appears in mobile app

### Test Case 2: Entry TO Address (Inside Geofence)

After Test Case 1, simulate tracker entering geofence:

```bash
# Test location INSIDE geofence
curl -X POST http://localhost:8000/api/v1/test/mock-location \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "tracker_id": "647b512f-92b8-4184-8a82-4321365d6336",
    "latitude": 51.375896,
    "longitude": -0.194597
  }' | jq
```

**Expected Result:**
- ENTRY event triggered
- Email sent to MailHog
- Alert appears in mobile app

## Verification Steps

### 1. Check MailHog (Email)

Open browser: http://localhost:8025

You should see email notifications with:
- Subject: "Geofence Alert: [POI Name]"
- Body: Details about entry/exit event

### 2. Check Mobile App

1. Open the app
2. Navigate to Alerts screen (bottom navigation)
3. See the new geofence alert notifications

### 3. Check Database

Query the alerts table:

```bash
docker exec ble_tracker_db psql -U ble_user -d ble_tracker -c \
  "SELECT id, event_type, latitude, longitude, is_read, created_at 
   FROM geofence_alerts 
   ORDER BY created_at DESC 
   LIMIT 5;"
```

## Automated Test Script

Run the automated test script:

```bash
cd /Users/carl/Documents/MobileCode/mobileGPS/gps-tracker
./test_geofence_notifications.sh
```

The script will:
1. Login and get auth token
2. Test location OUTSIDE geofence (EXIT)
3. Wait 3 seconds (debouncing)
4. Test location INSIDE geofence (ENTRY)
5. Display results and next steps

## Enable Email Notifications

Make sure email notifications are enabled in Settings:

1. Open mobile app
2. Tap hamburger menu (≡)
3. Tap "Settings"
4. Enable "Geofence Alerts" toggle

Or via API:

```bash
curl -X PUT http://localhost:8000/api/v1/user/preferences \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"email_alerts_enabled": true}'
```

## Coordinates Reference

### POI Origin Locations
- **All current POIs**: 51.375896, -0.194597 (SW London, Merton area)

### Test Coordinates

- **FAR OUTSIDE** (1km away): 51.385, -0.205
- **JUST OUTSIDE** (200m away): 51.377, -0.196
- **INSIDE** (exact center): 51.375896, -0.194597
- **EDGE** (just at radius): 51.3772, -0.1954

### Destination (for route POIs)
- 51.388925, -0.185216 (Wimbledon area)

## Troubleshooting

### No Alerts Triggered

1. **Check POI is armed**:
   ```bash
   docker exec ble_tracker_db psql -U ble_user -d ble_tracker -c \
     "SELECT p.name, ptl.is_armed 
      FROM pois p 
      JOIN poi_tracker_links ptl ON p.id = ptl.poi_id 
      WHERE ptl.tracker_id = '647b512f-92b8-4184-8a82-4321365d6336';"
   ```

2. **Check debouncing**: Wait at least 60 seconds between tests

3. **Check last alert**: The system tracks state changes (ENTRY → EXIT → ENTRY)

### No Emails Received

1. **Check email_alerts_enabled**: 
   ```bash
   docker exec ble_tracker_db psql -U ble_user -d ble_tracker -c \
     "SELECT email, email_alerts_enabled FROM users;"
   ```

2. **Check MailHog is running**:
   ```bash
   docker ps | grep mailhog
   ```

3. **Check backend logs**:
   ```bash
   docker logs --tail 50 ble_tracker_backend
   ```

## Next Steps

After successful testing:

1. **Implement Periodic Location Polling**: Add scheduled task to fetch tracker locations from MZone API every 10 minutes
2. **Test with Real GPS Data**: Use actual tracker movements
3. **Fine-tune Radius**: Adjust POI radius values based on real-world testing
4. **Add Push Notifications**: Consider adding mobile push notifications in addition to email
