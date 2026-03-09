from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base
import os
import enum

# Use String for UUIDs in SQLite, PostgreSQL UUID type for PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "")
use_sqlite = DATABASE_URL.startswith("sqlite")

if use_sqlite:
    # For SQLite, use String to store UUIDs
    def get_uuid_column():
        return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    def get_uuid_fk(table_col):
        return Column(String(36), ForeignKey(table_col), nullable=False)
else:
    # For PostgreSQL, use native UUID type
    from sqlalchemy.dialects.postgresql import UUID
    def get_uuid_column():
        return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    def get_uuid_fk(table_col):
        return Column(UUID(as_uuid=True), ForeignKey(table_col), nullable=False)

class User(Base):
    __tablename__ = "users"
    
    id = get_uuid_column()
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for passwordless users
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    email_alerts_enabled = Column(Boolean, default=True)  # Enable email alerts for geofence events
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    ble_tags = relationship("BLETag", back_populates="user")
    verification_pins = relationship("VerificationPIN", back_populates="user")
    pois = relationship("POI", back_populates="user")
    geofence_alerts = relationship("GeofenceAlert", back_populates="user")


class VerificationPIN(Base):
    __tablename__ = "verification_pins"
    
    id = get_uuid_column()
    user_id = get_uuid_fk("users.id")
    email = Column(String(255), nullable=False, index=True)
    pin = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="verification_pins")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = get_uuid_column()
    user_id = get_uuid_fk("users.id")
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(64), nullable=False, unique=True, index=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User")


class BLETag(Base):
    __tablename__ = "ble_tags"
    
    id = get_uuid_column()
    user_id = get_uuid_fk("users.id")
    imei = Column(String(50), unique=True, nullable=False, index=True)
    device_name = Column(String(100))
    device_model = Column(String(100))
    description = Column(String(255))  # Vehicle description from MZone API
    mac_address = Column(String(17))  # Format: XX:XX:XX:XX:XX:XX
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    latitude = Column(String(50))
    longitude = Column(String(50))
    battery_level = Column(Integer)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="ble_tags")
    poi_links = relationship("POITrackerLink", back_populates="tracker")
    geofence_alerts = relationship("GeofenceAlert", back_populates="tracker")


class GeofenceEventType(enum.Enum):
    ENTRY = "entry"
    EXIT = "exit"


class GeofenceState(enum.Enum):
    """Tracks the last known state of a tracker relative to a geofence"""
    UNKNOWN = "unknown"  # Initial state - not yet determined
    INSIDE = "inside"    # Tracker is inside the geofence
    OUTSIDE = "outside"  # Tracker is outside the geofence


class POIType(enum.Enum):
    SINGLE = "single"  # Single location POI (monitor entry/exit)
    ROUTE = "route"    # Delivery route (FROM origin TO destination)


class POI(Base):
    """Point of Interest / Geofence - supports both single locations and delivery routes"""
    __tablename__ = "pois"
    
    id = get_uuid_column()
    user_id = get_uuid_fk("users.id")
    name = Column(String(200), nullable=False)
    description = Column(Text)
    poi_type = Column(String(20), default='single', nullable=False)  # Store as string, not enum
    
    # Origin/FROM location (required for all types)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius = Column(Float, default=150.0)  # Default 150 meters
    address = Column(String(500))  # Full address or postcode used
    
    # Destination/TO location (only for ROUTE type)
    destination_latitude = Column(Float, nullable=True)
    destination_longitude = Column(Float, nullable=True)
    destination_radius = Column(Float, nullable=True)
    destination_address = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="pois")
    tracker_links = relationship("POITrackerLink", back_populates="poi")
    alerts = relationship("GeofenceAlert", back_populates="poi")


class POITrackerLink(Base):
    """Links POIs to trackers (ARM/DISARM)"""
    __tablename__ = "poi_tracker_links"
    
    id = get_uuid_column()
    poi_id = get_uuid_fk("pois.id")
    tracker_id = get_uuid_fk("ble_tags.id")
    is_armed = Column(Boolean, default=True)
    armed_at = Column(DateTime(timezone=True), server_default=func.now())
    disarmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # State tracking for alert generation
    last_known_state = Column(Enum(GeofenceState, values_callable=lambda x: [e.value for e in x]), default=GeofenceState.UNKNOWN, nullable=False)
    last_state_check = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    poi = relationship("POI", back_populates="tracker_links")
    tracker = relationship("BLETag", back_populates="poi_links")


class GeofenceAlert(Base):
    """Entry/Exit alerts for geofences"""
    __tablename__ = "geofence_alerts"
    
    id = get_uuid_column()
    poi_id = get_uuid_fk("pois.id")
    tracker_id = get_uuid_fk("ble_tags.id")
    user_id = get_uuid_fk("users.id")
    event_type = Column(Enum(GeofenceEventType), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    poi = relationship("POI", back_populates="alerts")
    tracker = relationship("BLETag", back_populates="geofence_alerts")
    user = relationship("User")
