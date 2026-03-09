"""
Background service that polls MZone API every 60 seconds to:
1. Update tracker positions in database
2. Check geofences automatically
3. Enable real-time alerts without manual refresh
"""

import asyncio
import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import BLETag, User
from app.services.mzone_service import MZoneService
from app.services.geofence_service import GeofenceService

logger = logging.getLogger(__name__)

class LocationPollerService:
    def __init__(self):
        self.mzone_service = MZoneService()
        self.running = False
        self.poll_interval = 60  # seconds
        
    async def start(self):
        """Start the background polling service"""
        self.running = True
        logger.info("🚀 Location Poller Service started - polling every 60 seconds")
        
        while self.running:
            try:
                await self._poll_locations()
            except Exception as e:
                logger.error(f"❌ Error in location polling cycle: {str(e)}")
            
            # Wait 60 seconds before next poll
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the background polling service"""
        self.running = False
        logger.info("🛑 Location Poller Service stopped")
    
    async def _poll_locations(self):
        """Poll all active trackers and check geofences"""
        db = SessionLocal()
        try:
            # Get all active trackers across all users
            trackers = db.query(BLETag).filter(BLETag.is_active == True).all()
            
            if not trackers:
                logger.debug("No active trackers to poll")
                return
            
            # Get IMEIs
            imeis = [tracker.imei for tracker in trackers]
            logger.info(f"📡 Polling {len(imeis)} trackers from MZone API")
            
            # Get locations from MZone API
            vehicles = self.mzone_service.get_vehicles_with_locations(imeis)
            
            # Create a map of IMEI -> vehicle data
            vehicle_map = {v.get('registration'): v for v in vehicles}
            
            # Update each tracker
            updated_count = 0
            for tracker in trackers:
                vehicle = vehicle_map.get(tracker.imei)
                if not vehicle:
                    continue
                
                position = vehicle.get('lastKnownPosition', {})
                if not position.get('latitude') or not position.get('longitude'):
                    continue
                
                # Update tracker position in database
                tracker.latitude = str(position.get('latitude'))
                tracker.longitude = str(position.get('longitude'))
                tracker.last_seen = datetime.utcnow()
                
                # Update description if available
                description = vehicle.get('description')
                if description and tracker.description != description:
                    tracker.description = description
                    tracker.updated_at = datetime.utcnow()
                
                # Get user for this tracker
                user = db.query(User).filter(User.id == tracker.user_id).first()
                if not user:
                    continue
                
                # Check geofences for this tracker
                try:
                    GeofenceService.check_geofences_for_tracker(
                        db,
                        str(tracker.id),
                        position.get('latitude'),
                        position.get('longitude'),
                        str(user.id)
                    )
                except Exception as e:
                    logger.error(f"❌ Error checking geofences for tracker {tracker.id}: {str(e)}")
                
                updated_count += 1
            
            # Commit all updates
            db.commit()
            logger.info(f"✅ Updated {updated_count} tracker positions and checked geofences")
            
        except Exception as e:
            logger.error(f"❌ Error in _poll_locations: {str(e)}")
            db.rollback()
        finally:
            db.close()


# Global instance
location_poller = LocationPollerService()
