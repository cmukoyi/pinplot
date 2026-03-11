#!/usr/bin/env python3
"""
Test script for /api/v1/trips endpoint
Tests trips data retrieval for IMEI: 868695060773007 (rhw.cheng@gmail.com)
"""

import requests
import json
from datetime import datetime, timedelta
import sys

# Configuration
BACKEND_URL = "http://localhost:8000"
API_ENDPOINT = f"{BACKEND_URL}/api/v1/trips"

# Test user credentials
TEST_EMAIL = "rhw.cheng@gmail.com"
TEST_PASSWORD = "your_password"  # Update if needed

# Test IMEI and vehicle info
TEST_IMEI = "868695060773007"

# Date range for trip query
START_DATE = (datetime.now() - timedelta(days=10)).isoformat().split('.')[0]
END_DATE = datetime.now().isoformat().split('.')[0]

def test_trips_api():
    """Test the Trips API endpoint"""
    
    print("=" * 80)
    print("Testing /api/v1/trips endpoint")
    print("=" * 80)
    print()
    
    # Step 1: Login to get JWT token
    print("Step 1: Getting authentication token...")
    print(f"  Email: {TEST_EMAIL}")
    
    login_response = requests.post(
        f"{BACKEND_URL}/api/v1/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        timeout=10
    )
    
    if login_response.status_code != 200:
        print(f"  ❌ Login failed: {login_response.status_code}")
        print(f"  Response: {login_response.text}")
        return False
    
    login_data = login_response.json()
    if not login_data.get('success'):
        print(f"  ❌ Login error: {login_data.get('message')}")
        return False
    
    auth_token = login_data.get('access_token')
    print(f"  ✅ Got token: {auth_token[:30]}...")
    print()
    
    # Step 2: Get BLE tags to find vehicle ID for IMEI
    print(f"Step 2: Looking up vehicle ID for IMEI {TEST_IMEI}...")
    
    tags_response = requests.get(
        f"{BACKEND_URL}/api/v1/ble-tags",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10
    )
    
    if tags_response.status_code != 200:
        print(f"  ❌ Failed to get tags: {tags_response.status_code}")
        print(f"  Response: {tags_response.text}")
        return False
    
    tags_data = tags_response.json()
    tags = tags_data.get('tags', [])
    
    # Find vehicle with matching IMEI
    vehicle_id = None
    vehicle_description = None
    
    for tag in tags:
        if tag.get('imei') == TEST_IMEI:
            vehicle_id = tag.get('vehicle_id') or tag.get('id')
            vehicle_description = tag.get('description') or tag.get('device_name')
            break
    
    if not vehicle_id:
        print(f"  ❌ No vehicle found with IMEI {TEST_IMEI}")
        print(f"  Available tags: {json.dumps(tags[:3], indent=2)}")
        return False
    
    print(f"  ✅ Found vehicle ID: {vehicle_id}")
    print(f"  Description: {vehicle_description}")
    print()
    
    # Step 3: Call /api/v1/trips with the vehicle ID
    print("Step 3: Fetching trips from API...")
    print(f"  Vehicle ID: {vehicle_id}")
    print(f"  Date range: {START_DATE} to {END_DATE}")
    print()
    
    trips_payload = {
        "vehicle_id": vehicle_id,
        "start_date": START_DATE,
        "end_date": END_DATE
    }
    
    print("  Request payload:")
    print(f"    {json.dumps(trips_payload, indent=4)}")
    print()
    
    trips_response = requests.post(
        API_ENDPOINT,
        json=trips_payload,
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30
    )
    
    print(f"  Status Code: {trips_response.status_code}")
    print()
    
    if trips_response.status_code != 200:
        print(f"  ❌ API Error: {trips_response.status_code}")
        print(f"  Response: {trips_response.text}")
        return False
    
    trips_data = trips_response.json()
    
    if not trips_data.get('success'):
        print(f"  ❌ API returned error: {trips_data.get('error')}")
        print(f"  Details: {trips_data}")
        return False
    
    # Step 4: Display results
    print("=" * 80)
    print("✅ SUCCESS - Trips API Response")
    print("=" * 80)
    print()
    
    print(f"Total trips available: {trips_data.get('total_count')}")
    print(f"Trips returned: {trips_data.get('returned_count')}")
    print()
    
    trips = trips_data.get('trips', [])
    
    if not trips:
        print("  ⚠️ No trips found for this date range")
        return True
    
    print(f"Showing first {min(5, len(trips))} trips:")
    print()
    
    for i, trip in enumerate(trips[:5], 1):
        print(f"Trip {i}:")
        print(f"  ID: {trip.get('id')}")
        print(f"  Vehicle: {trip.get('vehicle_Description')}")
        print(f"  Driver: {trip.get('driver_Description', 'N/A')}")
        print(f"  Start: {trip.get('startUtcTimestamp')} - {trip.get('startLocationDescription', 'Unknown location')}")
        print(f"  End: {trip.get('endUtcTimestamp')} - {trip.get('endLocationDescription', 'Unknown location')}")
        print(f"  Distance: {trip.get('distance', 0):.2f} km")
        print(f"  Duration: {trip.get('duration', 0)} seconds ({trip.get('duration', 0) / 60:.0f} minutes)")
        print()
    
    # Show full JSON for detailed inspection
    print("=" * 80)
    print("Full API Response (formatted JSON):")
    print("=" * 80)
    print(json.dumps(trips_data, indent=2))
    
    return True


if __name__ == "__main__":
    try:
        success = test_trips_api()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to backend at", BACKEND_URL)
        print("   Make sure the backend is running:")
        print("   cd C:\\Users\\Carlos Mukoyi\\Documents\\code\\beaconTelematics\\gps-tracker\\backend")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
