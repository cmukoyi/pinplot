"""
MZone API Service
Handles OAuth authentication and vehicle data fetching from MZone API
"""
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote

class MZoneService:
    def __init__(self):
        self.token_url = os.getenv('MZONE_TOKEN_URL', 'https://login.mzoneweb.net/connect/token')
        self.client_id = os.getenv('MZONE_CLIENT_ID')
        self.client_secret = os.getenv('MZONE_CLIENT_SECRET')
        self.username = os.getenv('MZONE_USERNAME')
        self.password = os.getenv('MZONE_PASSWORD')
        self.scope = os.getenv('MZONE_SCOPE', 'mz6-api.all mz_username')
        self.grant_type = os.getenv('MZONE_GRANT_TYPE', 'password')
        self.api_base = os.getenv('MZONE_API_BASE', 'https://live.mzoneweb.net/mzone62.api')
        self.vehicle_group_id = os.getenv('MZONE_VEHICLE_GROUP_ID')
        
        # Token cache
        self.token_cache = {
            'token': None,
            'expires_at': None
        }
        
        self.debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    def get_oauth_token(self) -> Optional[str]:
        """Get OAuth token from cache or fetch new one"""
        try:
            # Check if cached token is still valid
            if self.token_cache['token'] and self.token_cache['expires_at']:
                if datetime.now() < self.token_cache['expires_at']:
                    if self.debug:
                        print(f"✅ Using cached token (expires at {self.token_cache['expires_at']})")
                    return self.token_cache['token']
            
            # Fetch new token
            if self.debug:
                print("🔐 Fetching new OAuth token from MZone...")
            
            payload = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': self.grant_type,
                'username': self.username,
                'password': self.password,
                'scope': self.scope
            }
            
            # URL encode the payload
            payload_str = '&'.join([f"{k}={quote(str(v))}" for k, v in payload.items()])
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            response = requests.post(
                self.token_url,
                data=payload_str,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                
                # Cache token with expiration
                self.token_cache['token'] = token
                self.token_cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in - 60)
                
                if self.debug:
                    print(f"✅ Token obtained successfully (expires in {expires_in}s)")
                
                return token
            else:
                if self.debug:
                    print(f"❌ OAuth error: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            if self.debug:
                print(f"❌ Error fetching OAuth token: {str(e)}")
            return None
    
    def get_all_vehicles(self) -> Optional[Dict]:
        """Fetch all vehicles from MZone API"""
        try:
            token = self.get_oauth_token()
            if not token:
                return None
            
            url = f"{self.api_base}/Vehicles"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            params = {
                'vehicleGroup_Id': self.vehicle_group_id
            }
            
            if self.debug:
                print(f"📡 Fetching vehicles from MZone API...")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if self.debug:
                    vehicle_count = data.get('@odata.count', len(data.get('value', [])))
                    print(f"✅ Fetched {vehicle_count} vehicles from MZone")
                return data
            else:
                if self.debug:
                    print(f"❌ Error fetching vehicles: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            if self.debug:
                print(f"❌ Error in get_all_vehicles: {str(e)}")
            return None
    
    def get_vehicle_locations(self, vehicle_ids: List[str]) -> Optional[Dict]:
        """Fetch locations for specific vehicles"""
        try:
            token = self.get_oauth_token()
            if not token:
                return None
            
            url = f"{self.api_base}/LastKnownPositions"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            # Build filter for multiple vehicle IDs (no guid wrapper needed)
            filters = [f"vehicle_Id eq {vid}" for vid in vehicle_ids]
            filter_str = ' or '.join(filters)
            
            params = {
                '$filter': filter_str
            }
            
            if self.debug:
                print(f"📍 Fetching locations for {len(vehicle_ids)} vehicles...")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if self.debug:
                    location_count = len(data.get('value', []))
                    print(f"✅ Fetched {location_count} locations")
                return data
            else:
                if self.debug:
                    print(f"❌ Error fetching locations: {response.status_code}")
                return None
        
        except Exception as e:
            if self.debug:
                print(f"❌ Error in get_vehicle_locations: {str(e)}")
            return None
    
    def get_vehicles_with_locations(self, user_imeis: List[str]) -> List[Dict]:
        """
        Get vehicles matching user's IMEIs with their locations
        Returns list of vehicle objects with location data
        """
        try:
            # Get all vehicles
            vehicles_data = self.get_all_vehicles()
            if not vehicles_data:
                return []
            
            all_vehicles = vehicles_data.get('value', [])
            if self.debug:
                print(f"\n{'='*70}")
                print(f"📋 MZone returned {len(all_vehicles)} total vehicles")
                print(f"🔍 Looking for IMEIs: {user_imeis}")
                print(f"{'='*70}")
                for v in all_vehicles:
                    reg = v.get('registration', 'NO_REG')
                    unit_desc = v.get('unit_Description', 'NO_UNIT_DESC')
                    desc = v.get('description', 'NO_DESC')
                    vid = v.get('id', 'NO_ID')
                    # Check BOTH registration AND unit_Description
                    match_status = '✅ MATCH' if (reg in user_imeis or unit_desc in user_imeis) else '   '
                    print(f"{match_status} | registration={reg} | unit_Description={unit_desc} | desc={desc} | id={vid}")
            
            # Filter vehicles by user's IMEIs
            # IMPORTANT: MZone can store IMEI in EITHER 'registration' OR 'unit_Description' field
            # We must check BOTH fields to find all user vehicles
            matched_vehicles = []
            vehicle_ids = []
            
            if self.debug:
                print(f"\n{'='*70}")
                print(f"🔎 Filtering vehicles by user IMEIs...")
                print(f"{'='*70}")
            
            for vehicle in all_vehicles:
                registration = vehicle.get('registration', '')
                unit_description = vehicle.get('unit_Description', '')
                
                # Check if IMEI matches either registration OR unit_Description
                if registration in user_imeis or unit_description in user_imeis:
                    matched_vehicles.append(vehicle)
                    vehicle_ids.append(vehicle.get('id'))
                    matched_field = 'registration' if registration in user_imeis else 'unit_Description'
                    matched_value = registration if registration in user_imeis else unit_description
                    if self.debug:
                        print(f"✅ MATCHED: {vehicle.get('description')} | {matched_field}={matched_value} | ID: {vehicle.get('id')}")
            
            if not matched_vehicles:
                if self.debug:
                    print(f"{'='*70}")
                    print(f"⚠️  NO MATCHES FOUND!")
                    print(f"   User IMEIs: {user_imeis}")
                    print(f"   Available registrations: {[v.get('registration') for v in all_vehicles[:10]]}")
                    print(f"{'='*70}\n")
                return []
            
            if self.debug:
                print(f"🎯 Filtered to {len(matched_vehicles)} vehicles for user")
            
            # Get locations for matched vehicles
            locations_data = self.get_vehicle_locations(vehicle_ids)
            if not locations_data:
                # Return vehicles without location data
                return matched_vehicles
            
            # Merge location data into vehicles
            locations = {loc.get('vehicle_Id'): loc for loc in locations_data.get('value', [])}
            
            for vehicle in matched_vehicles:
                vehicle_id = vehicle.get('id')
                if vehicle_id in locations:
                    vehicle['lastKnownPosition'] = locations[vehicle_id]
            
            return matched_vehicles
        
        except Exception as e:
            if self.debug:
                print(f"❌ Error in get_vehicles_with_locations: {str(e)}")
            return []


# Singleton instance
mzone_service = MZoneService()
