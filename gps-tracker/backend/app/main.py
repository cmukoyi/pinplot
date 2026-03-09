from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
import random
import secrets
import os
import logging
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models import User, VerificationPIN, BLETag, POI, POITrackerLink, GeofenceAlert, PasswordResetToken, GeofenceState
from app.auth import verify_password, get_password_hash, create_access_token, decode_token
from app.services.email_service import EmailService
from app.services.mzone_service import mzone_service
from app.services.geofence_service import GeofenceService
from app.services.location_poller_service import location_poller
import asyncio
from app.schemas.poi import (
    POICreate, POIUpdate, POIResponse, POIWithArmedStatus,
    POITrackerLinkCreate, POITrackerLinkResponse,
    GeofenceAlertResponse, AlertsListResponse,
    PostcodeSearchRequest, PostcodeSearchResponse
)

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_admin: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SendVerificationCodeRequest(BaseModel):
    email: EmailStr

class VerifyPINRequest(BaseModel):
    email: EmailStr
    pin: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    email_verified: bool
    email_alerts_enabled: bool
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class MockLocationTestRequest(BaseModel):
    tracker_id: str
    latitude: float
    longitude: float

class BLETagCreate(BaseModel):
    imei: str
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    description: Optional[str] = None
    mac_address: Optional[str] = None

class BLETagResponse(BaseModel):
    id: str
    imei: str
    device_name: Optional[str]
    device_model: Optional[str]
    description: Optional[str]
    mac_address: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    battery_level: Optional[int]
    added_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: lambda v: str(v)
        }
    
    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to Pydantic model with UUID to string conversion"""
        return cls(
            id=str(obj.id),
            imei=obj.imei,
            device_name=obj.device_name,
            device_model=obj.device_model,
            description=obj.description,
            mac_address=obj.mac_address,
            is_active=obj.is_active,
            last_seen=obj.last_seen,
            battery_level=obj.battery_level,
            added_at=obj.added_at
        )

class BLETagWithUser(BaseModel):
    """BLE Tag with associated user information for admin billing"""
    id: str
    imei: str
    device_name: Optional[str]
    device_model: Optional[str]
    is_active: bool
    added_at: datetime
    activated_at: datetime  # Alias for added_at for clarity
    user_id: str
    user_email: str
    
    class Config:
        from_attributes = True
        json_encoders = {
            UUID: lambda v: str(v)
        }
    
    @classmethod
    def from_db_model(cls, tag, user_email: str):
        """Create from BLETag and user email with UUID conversion"""
        return cls(
            id=str(tag.id),
            imei=tag.imei,
            device_name=tag.device_name,
            device_model=tag.device_model,
            is_active=tag.is_active,
            added_at=tag.added_at,
            activated_at=tag.added_at,
            user_id=str(tag.user_id),
            user_email=user_email
        )
    user_name: str
    
    class Config:
        from_attributes = True

class UserWithTags(BaseModel):
    """User information with their BLE tags for admin billing"""
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    is_active: bool
    created_at: datetime
    tag_count: int
    tags: List[BLETagResponse]
    
    class Config:
        from_attributes = True

app = FastAPI(
    title="BLE Tracker API",
    version="0.1.0",
    description="Backend API for BLE tag tracking system"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize email service
email_service = EmailService()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized!")
    print(f"SMTP configured: {email_service.smtp_host}:{email_service.smtp_port}")
    print("MailHog Web UI available at: http://localhost:8025")
    
    # Start background location poller
    asyncio.create_task(location_poller.start())
    print("🚀 Location Poller Service started (60-second interval)")

@app.on_event("shutdown")
def shutdown_event():
    location_poller.stop()
    print("🛑 Location Poller Service stopped")

# Demo data - simulating BLE tags
DEMO_TAGS = [
    {
        "id": "tag-001",
        "name": "Office Tag",
        "battery": 85,
        "status": "active",
        "last_seen": "2024-02-28T10:30:00Z"
    },
    {
        "id": "tag-002",
        "name": "Car Tag",
        "battery": 92,
        "status": "active",
        "last_seen": "2024-02-28T10:25:00Z"
    },
    {
        "id": "tag-003",
        "name": "Backpack Tag",
        "battery": 67,
        "status": "active",
        "last_seen": "2024-02-28T10:28:00Z"
    }
]

# Demo locations
DEMO_LOCATIONS = {
    "tag-001": {"latitude": 37.7749, "longitude": -122.4194, "address": "San Francisco, CA"},
    "tag-002": {"latitude": 37.7849, "longitude": -122.4094, "address": "Near Golden Gate"},
    "tag-003": {"latitude": 37.7649, "longitude": -122.4294, "address": "Mission District"}
}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "BLE Tracker API",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# Authentication endpoints
@app.post("/api/v1/auth/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        # If user exists but has no password (from email verification), update it
        if existing_user.hashed_password is None:
            existing_user.hashed_password = get_password_hash(user_data.password)
            existing_user.first_name = user_data.first_name
            existing_user.last_name = user_data.last_name
            existing_user.is_admin = user_data.is_admin
            existing_user.email_verified = True
            db.commit()
            db.refresh(existing_user)
            
            # Generate token
            access_token = create_access_token(data={"sub": str(existing_user.id)})
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new user
    db_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_admin=user_data.is_admin,
        email_verified=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Generate token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh JWT token for active users.
    Returns a new token with extended expiration.
    Call this endpoint before the current token expires.
    """
    # Create new token with same user ID
    access_token = create_access_token(data={"sub": str(current_user.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/send-verification-code")
def send_verification_code(request: SendVerificationCodeRequest, db: Session = Depends(get_db)):
    """Send verification PIN to email"""
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    
    # If user exists and already has a password, they're fully registered
    if user and user.hashed_password is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please sign in instead."
        )
    
    # Generate 6-digit PIN
    pin = email_service.generate_pin()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # If user doesn't exist, create a temporary record
    if not user:
        user = User(
            email=request.email,
            hashed_password=None,  # Will be set after verification
            email_verified=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Invalidate old PINs
    db.query(VerificationPIN).filter(
        VerificationPIN.email == request.email,
        VerificationPIN.is_used == False
    ).update({"is_used": True})
    
    # Create new PIN
    verification = VerificationPIN(
        user_id=user.id,
        email=request.email,
        pin=pin,
        expires_at=expires_at
    )
    db.add(verification)
    db.commit()
    
    # Send email
    success = email_service.send_verification_pin(request.email, pin)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )
    
    return {
        "success": True,
        "message": "Verification code sent to email",
        "expires_in_minutes": 10
    }

@app.post("/api/v1/auth/verify-pin", response_model=Token)
def verify_pin(request: VerifyPINRequest, db: Session = Depends(get_db)):
    """Verify PIN and create/login user"""
    # Find valid PIN
    verification = db.query(VerificationPIN).filter(
        VerificationPIN.email == request.email,
        VerificationPIN.pin == request.pin,
        VerificationPIN.is_used == False,
        VerificationPIN.expires_at > datetime.utcnow()
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Mark PIN as used
    verification.is_used = True
    
    # Get or update user
    user = db.query(User).filter(User.id == verification.user_id).first()
    user.email_verified = True
    user.is_active = True
    
    db.commit()
    db.refresh(user)
    
    # Send welcome email if it's a new user (only if email is configured)
    import os
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    if not user.first_name and not debug:
        email_service.send_welcome_email(user.email)
    
    # Generate access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset - sends email with reset link"""
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Don't reveal that the user doesn't exist for security
        return {
            "success": True,
            "message": "If an account exists with this email, a password reset link has been sent."
        }
    
    # Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    # Invalidate old tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False
    ).update({"is_used": True})
    db.commit()
    
    # Create new reset token
    password_reset = PasswordResetToken(
        user_id=user.id,
        email=user.email,
        token=reset_token,
        expires_at=expires_at
    )
    db.add(password_reset)
    db.commit()
    
    # Send password reset email
    success = email_service.send_password_reset_email(
        to_email=user.email,
        reset_token=reset_token,
        first_name=user.first_name
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )
    
    return {
        "success": True,
        "message": "If an account exists with this email, a password reset link has been sent."
    }

@app.post("/api/v1/auth/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using reset token"""
    # Find valid reset token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.is_used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate password length
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    
    # Mark token as used
    reset_token.is_used = True
    
    db.commit()
    
    return {
        "success": True,
        "message": "Password has been reset successfully"
    }

@app.get("/api/v1/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user

class UserPreferencesUpdate(BaseModel):
    email_alerts_enabled: Optional[bool] = None

@app.put("/api/v1/user/preferences", response_model=UserResponse)
def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences (email alerts, etc.)"""
    if preferences.email_alerts_enabled is not None:
        current_user.email_alerts_enabled = preferences.email_alerts_enabled
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

class EmailUpdate(BaseModel):
    email: str

@app.put("/api/v1/user/email", response_model=UserResponse)
def update_user_email(
    email_data: EmailUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's email address"""
    # Validate email format
    if not email_data.email or '@' not in email_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Check if email already exists for another user
    existing_user = db.query(User).filter(
        User.email == email_data.email,
        User.id != current_user.id
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use by another account"
        )
    
    # Update email
    current_user.email = email_data.email
    current_user.email_verified = False  # Require re-verification for new email
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

# BLE Tag Management endpoints
@app.post("/api/v1/ble-tags", response_model=BLETagResponse)
def add_ble_tag(
    tag_data: BLETagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new BLE tag to user's account"""
    # Check if IMEI already exists
    existing_tag = db.query(BLETag).filter(BLETag.imei == tag_data.imei).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This IMEI is already registered"
        )
    
    # Create new tag
    ble_tag = BLETag(
        user_id=current_user.id,
        imei=tag_data.imei,
        device_name=tag_data.device_name,
        device_model=tag_data.device_model,
        mac_address=tag_data.mac_address
    )
    db.add(ble_tag)
    db.commit()
    db.refresh(ble_tag)
    
    return ble_tag

@app.get("/api/v1/ble-tags", response_model=List[BLETagResponse])
def list_user_ble_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all BLE tags for current user"""
    tags = db.query(BLETag).filter(
        BLETag.user_id == current_user.id,
        BLETag.is_active == True
    ).all()
    
    # Convert ORM objects to Pydantic models with UUID serialization
    return [BLETagResponse.from_orm(tag) for tag in tags]

@app.get("/api/v1/ble-tags/{tag_id}", response_model=BLETagResponse)
def get_ble_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific BLE tag details"""
    tag = db.query(BLETag).filter(
        BLETag.id == tag_id,
        BLETag.user_id == current_user.id
    ).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return tag

@app.get("/api/v1/validate-imei/{imei}")
def validate_imei(
    imei: str,
    current_user: User = Depends(get_current_user)
):
    """
    Validate IMEI by checking if it exists in the MProfiler API
    Returns 200 if valid, 404 if not found
    """
    import requests
    
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Validate IMEI format
    if not imei.isdigit() or len(imei) != 15:
        if debug:
            print(f"❌ Invalid IMEI format: {imei} (length: {len(imei)})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid IMEI format. Must be 15 digits."
        )
    
    try:
        # Call MProfiler API to validate IMEI
        validation_url = f'https://live.scopemp.net/Scope.MProfiler.Api/v1/UnitExtendedProperties/{imei}'
        headers = {
            'Authorization': 'Basic T0NJX1Njb3BlVUtfTVo6T0NJU2NvcGVVS01aMDEh'
        }
        
        if debug:
            print(f"🔍 Validating IMEI: {imei}")
            print(f"📡 API URL: {validation_url}")
        
        response = requests.get(validation_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            if debug:
                print(f"✅ IMEI {imei} is valid")
            return {
                "success": True,
                "message": "IMEI is valid",
                "imei": imei
            }
        elif response.status_code == 404:
            if debug:
                print(f"❌ IMEI {imei} not found")
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "IMEI unknown error"
                }
            )
        else:
            if debug:
                print(f"⚠️ IMEI validation failed with status: {response.status_code}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Validation service error: {response.status_code}"
                }
            )
                
    except requests.exceptions.Timeout:
        if debug:
            print(f"⏱️ IMEI validation timeout for {imei}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Validation service timeout. Please try again."
            }
        )
    except requests.exceptions.RequestException as e:
        if debug:
            print(f"❌ IMEI validation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Unable to validate IMEI. Please try again."
            }
        )
    except Exception as e:
        if debug:
            print(f"❌ Unexpected error during IMEI validation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "An unexpected error occurred"
            }
        )

@app.delete("/api/v1/ble-tags/{tag_id}")
def remove_ble_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove BLE tag from user's account"""
    tag = db.query(BLETag).filter(
        BLETag.id == tag_id,
        BLETag.user_id == current_user.id
    ).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Soft delete
    tag.is_active = False
    db.commit()
    
    return {"success": True, "message": "Tag removed successfully"}

# Admin endpoints
@app.get("/api/v1/admin/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """List all users (admin only - auth temporarily disabled for development)"""
    # TODO: Re-enable authentication in production
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not enough permissions"
    #     )
    
    users = db.query(User).all()
    return users

@app.get("/api/v1/admin/billing/tags", response_model=List[BLETagWithUser])
def list_all_tags_with_users(db: Session = Depends(get_db)):
    """
    List all BLE tags with user information for billing purposes
    Shows: IMEI, activation date, user details
    """
    tags = db.query(BLETag).join(User).all()
    
    result = []
    for tag in tags:
        full_name = f"{tag.user.first_name or ''} {tag.user.last_name or ''}".strip()
        if not full_name:
            full_name = tag.user.email.split('@')[0]
        
        result.append({
            "id": str(tag.id),
            "imei": tag.imei,
            "device_name": tag.device_name,
            "device_model": tag.device_model,
            "is_active": tag.is_active,
            "added_at": tag.added_at,
            "activated_at": tag.added_at,  # Same as added_at, just clearer naming
            "user_id": str(tag.user_id),
            "user_email": tag.user.email,
            "user_name": full_name
        })
    
    return result

@app.get("/api/v1/admin/billing/users", response_model=List[UserWithTags])
def list_users_with_tags(db: Session = Depends(get_db)):
    """
    List all users with their BLE tags and tag count for billing purposes
    Shows: User details, tag count, all associated tags with activation dates
    """
    users = db.query(User).all()
    
    result = []
    for user in users:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if not full_name:
            full_name = user.email.split('@')[0]
        
        # Convert tags to proper format with string IDs
        tags_list = []
        for tag in user.ble_tags:
            tags_list.append({
                "id": str(tag.id),
                "imei": tag.imei,
                "device_name": tag.device_name,
                "device_model": tag.device_model,
                "mac_address": tag.mac_address,
                "is_active": tag.is_active,
                "last_seen": tag.last_seen,
                "battery_level": tag.battery_level,
                "added_at": tag.added_at
            })
        
        result.append({
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": full_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "tag_count": len(user.ble_tags),
            "tags": tags_list
        })
    
    return result

# Demo tag endpoints (will be replaced with external API calls)
@app.get("/api/v1/tags")
def get_tags(current_user: User = Depends(get_current_user)) -> List[Dict]:
    """
    Get all BLE tags (demo data)
    In production, this will proxy to external BLE API
    """
    return DEMO_TAGS

@app.get("/api/v1/tags/{tag_id}")
def get_tag_details(tag_id: str, current_user: User = Depends(get_current_user)) -> Dict:
    """
    Get specific tag details (demo data)
    """
    tag = next((t for t in DEMO_TAGS if t["id"] == tag_id), None)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag

@app.get("/api/v1/tags/{tag_id}/location")
def get_tag_location(tag_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict:
    """
    Get latest GPS location of a tag (demo data)
    """
    # Verify tag belongs to user
    tag = db.query(BLETag).filter(
        BLETag.id == tag_id,
        BLETag.user_id == current_user.id
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Check if tag has stored location
    if tag.latitude and tag.longitude:
        location = {
            "latitude": float(tag.latitude),
            "longitude": float(tag.longitude),
            "address": f"Location for {tag.device_name or tag.imei}"
        }
    # Otherwise, generate demo location based on tag_id for consistency
    elif tag_id in DEMO_LOCATIONS:
        location = DEMO_LOCATIONS[tag_id].copy()
    else:
        # Generate consistent demo location based on tag_id hash
        import hashlib
        hash_val = int(hashlib.md5(tag_id.encode()).hexdigest()[:8], 16)
        # San Francisco area: 37.7-37.8, -122.5 to -122.4
        lat = 37.7 + (hash_val % 1000) / 10000.0
        lon = -122.5 + (hash_val // 1000 % 1000) / 10000.0
        location = {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "address": f"Demo location for {tag.device_name or tag.imei}"
        }
    
    location["tag_id"] = tag_id
    location["timestamp"] = datetime.utcnow().isoformat()
    location["accuracy"] = round(random.uniform(5.0, 15.0), 2)
    
    return location

@app.get("/api/v1/tags/{tag_id}/history")
def get_location_history(tag_id: str, current_user: User = Depends(get_current_user), limit: int = 10) -> List[Dict]:
    """
    Get location history (demo data)
    """
    if tag_id not in DEMO_LOCATIONS:
        return []
    
    base_location = DEMO_LOCATIONS[tag_id]
    history = []
    
    for i in range(limit):
        history.append({
            "latitude": base_location["latitude"] + random.uniform(-0.01, 0.01),
            "longitude": base_location["longitude"] + random.uniform(-0.01, 0.01),
            "accuracy": round(random.uniform(5.0, 15.0), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "battery": random.randint(60, 100)
        })
    
    return history


# ============================================================================
# Mobile App Compatibility Endpoints (without /v1)
# ============================================================================

@app.post("/api/auth/send-pin")
def send_pin_compat(request: SendVerificationCodeRequest, db: Session = Depends(get_db)):
    """Mobile app compatibility endpoint for send-verification-code"""
    return send_verification_code(request, db)


@app.post("/api/auth/verify-pin")
def verify_pin_compat(request: VerifyPINRequest, db: Session = Depends(get_db)):
    """Mobile app compatibility endpoint for verify-pin"""
    result = verify_pin(request, db)
    # Return with 'token' field instead of 'access_token' for mobile app compatibility
    return {
        "token": result["access_token"],
        "access_token": result["access_token"],
        "token_type": "bearer",
        "success": True
    }


@app.get("/api/auth/me", response_model=UserResponse)
def get_me_compat(current_user: User = Depends(get_current_user)):
    """Mobile app compatibility endpoint for current user"""
    return current_user


@app.post("/api/tags/add")
def add_tag_compat(
    tag_data: BLETagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mobile app compatibility endpoint for adding tags"""
    import requests
    
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    try:
        # Validate IMEI format
        if not tag_data.imei.isdigit() or len(tag_data.imei) != 15:
            if debug:
                print(f"❌ Invalid IMEI format: {tag_data.imei} (length: {len(tag_data.imei)})")
            return {
                "success": False,
                "error": "Invalid IMEI format. Must be 15 digits."
            }
        
        # Check if IMEI already exists
        existing_tag = db.query(BLETag).filter(BLETag.imei == tag_data.imei).first()
        if existing_tag:
            if debug:
                print(f"❌ IMEI {tag_data.imei} already registered")
            return {
                "success": False,
                "error": "This IMEI is already registered"
            }
        
        # Validate IMEI with MProfiler API before adding
        validation_url = f'https://live.scopemp.net/Scope.MProfiler.Api/v1/UnitExtendedProperties/{tag_data.imei}'
        headers = {
            'Authorization': 'Basic T0NJX1Njb3BlVUtfTVo6T0NJU2NvcGVVS01aMDEh'
        }
        
        if debug:
            print(f"🔍 Validating IMEI before adding: {tag_data.imei}")
            print(f"📡 API URL: {validation_url}")
        
        try:
            validation_response = requests.get(validation_url, headers=headers, timeout=10)
            
            if validation_response.status_code == 404:
                if debug:
                    print(f"❌ IMEI {tag_data.imei} not found in MProfiler")
                return {
                    "success": False,
                    "error": "IMEI not found in tracking system. Please check the IMEI and try again."
                }
            elif validation_response.status_code != 200:
                if debug:
                    print(f"⚠️ IMEI validation returned status: {validation_response.status_code}")
                return {
                    "success": False,
                    "error": f"Unable to validate IMEI (status: {validation_response.status_code}). Please try again."
                }
            
            if debug:
                print(f"✅ IMEI {tag_data.imei} validated successfully")
                
        except requests.exceptions.Timeout:
            if debug:
                print(f"⏱️ IMEI validation timeout for {tag_data.imei}")
            return {
                "success": False,
                "error": "Validation service timeout. Please try again."
            }
        except requests.exceptions.RequestException as e:
            if debug:
                print(f"❌ IMEI validation error: {str(e)}")
            return {
                "success": False,
                "error": "Unable to validate IMEI. Please check your connection and try again."
            }
        
        # IMEI is valid, create new tag
        ble_tag = BLETag(
            user_id=current_user.id,
            imei=tag_data.imei,
            device_name=tag_data.device_name,
            device_model=tag_data.device_model,
            description=tag_data.description,
            mac_address=tag_data.mac_address
        )
        db.add(ble_tag)
        db.commit()
        db.refresh(ble_tag)
        
        if debug:
            print(f"✅ Tag added successfully: {tag_data.imei}")
        
        return {
            "success": True,
            "message": "Tag added successfully",
            "tag": {
                "id": str(ble_tag.id),
                "imei": ble_tag.imei,
                "added_date": ble_tag.added_at.isoformat()
            }
        }
    except Exception as e:
        if debug:
            print(f"❌ Error adding tag: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/tags/list")
def list_tags_compat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mobile app compatibility endpoint for listing tags"""
    try:
        tags = db.query(BLETag).filter(
            BLETag.user_id == current_user.id,
            BLETag.is_active == True
        ).all()
        
        return {
            "success": True,
            "tags": [
                {
                    "id": str(tag.id),
                    "imei": tag.imei,
                    "added_date": tag.added_at.isoformat(),
                    "device_name": tag.device_name,
                    "description": tag.description
                }
                for tag in tags
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.delete("/api/tags/remove/{imei}")
def remove_tag_compat(
    imei: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mobile app compatibility endpoint for removing tags"""
    try:
        tag = db.query(BLETag).filter(
            BLETag.user_id == current_user.id,
            BLETag.imei == imei
        ).first()
        
        if not tag:
            return {
                "success": False,
                "error": "Tag not found"
            }
        
        # Soft delete
        tag.is_active = False
        db.commit()
        
        return {
            "success": True,
            "message": "Tag removed successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/vehicles")
def get_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vehicles from cached database (updated by background poller every 60 seconds)
    Returns last known positions without calling MZone API on every request
    """
    import os
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    try:
        # Get user's trackers from database (already updated by background poller)
        tags = db.query(BLETag).filter(
            BLETag.user_id == current_user.id,
            BLETag.is_active == True
        ).all()
        
        if debug:
            print(f"\n{'='*60}")
            print(f"📱 User {current_user.email} requesting vehicles (from cache)")
            print(f"🏷️  User has {len(tags)} tags")
            print(f"{'='*60}\n")
        
        if not tags:
            return {
                "success": True,
                "vehicles": [],
                "message": "No tags registered. Please add vehicle IMEIs first."
            }
        
        # Format response from cached database data
        formatted_vehicles = []
        for tag in tags:
            # Build lastKnownPosition from cached data
            last_known_position = None
            if tag.latitude and tag.longitude:
                try:
                    last_known_position = {
                        "latitude": float(tag.latitude),
                        "longitude": float(tag.longitude),
                        "utcTimestamp": tag.last_seen.isoformat() if tag.last_seen else None,
                        "speed": None,  # Not stored in database currently
                        "heading": None,  # Not stored in database currently
                        "locationDescription": None,  # Not stored in database currently
                    }
                except (ValueError, TypeError):
                    pass
            
            formatted_vehicles.append({
                "id": str(tag.id),  # Use BLETag database ID
                "description": tag.description,
                "registration": tag.imei,
                "ignitionOn": False,  # Not stored in database currently
                "lastKnownPosition": last_known_position
            })
        
        if debug:
            print(f"✅ Returning {len(formatted_vehicles)} vehicles from cache")
        
        return {
            "success": True,
            "count": len(formatted_vehicles),
            "vehicles": formatted_vehicles
        }
    
    except Exception as e:
        if debug:
            print(f"❌ Error in /api/vehicles: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "vehicles": []
        }
        
        return {
            "success": True,
            "count": len(formatted_vehicles),
            "vehicles": formatted_vehicles
        }
    
    except Exception as e:
        if debug:
            print(f"❌ Error in /api/vehicles: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "vehicles": []
        }


# ==================== POI / Geofence Management ====================

@app.post("/api/v1/pois", response_model=POIResponse)
def create_poi(
    poi_data: POICreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new Point of Interest (POI) / Geofence"""
    poi = POI(
        user_id=str(current_user.id),
        name=poi_data.name,
        description=poi_data.description,
        poi_type=poi_data.poi_type,
        latitude=poi_data.latitude,
        longitude=poi_data.longitude,
        radius=poi_data.radius,
        address=poi_data.address,
        destination_latitude=poi_data.destination_latitude,
        destination_longitude=poi_data.destination_longitude,
        destination_radius=poi_data.destination_radius,
        destination_address=poi_data.destination_address,
        is_active=True
    )
    
    db.add(poi)
    db.commit()
    db.refresh(poi)
    
    return POIResponse(
        id=str(poi.id),
        user_id=str(poi.user_id),
        name=poi.name,
        description=poi.description,
        poi_type=poi.poi_type,
        latitude=poi.latitude,
        longitude=poi.longitude,
        radius=poi.radius,
        address=poi.address,
        destination_latitude=poi.destination_latitude,
        destination_longitude=poi.destination_longitude,
        destination_radius=poi.destination_radius,
        destination_address=poi.destination_address,
        is_active=poi.is_active,
        created_at=poi.created_at,
        updated_at=poi.updated_at
    )


@app.get("/api/v1/pois", response_model=List[POIWithArmedStatus])
def list_pois(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all POIs for the current user with armed status"""
    pois = db.query(POI).filter(POI.user_id == str(current_user.id)).all()
    
    result = []
    for poi in pois:
        # Get armed trackers for this POI
        armed_links = db.query(POITrackerLink).filter(
            POITrackerLink.poi_id == poi.id,
            POITrackerLink.is_armed == True
        ).all()
        
        armed_tracker_ids = [str(link.tracker_id) for link in armed_links]
        
        result.append(POIWithArmedStatus(
            id=str(poi.id),
            user_id=str(poi.user_id),
            name=poi.name,
            description=poi.description,
            poi_type=poi.poi_type,
            latitude=poi.latitude,
            longitude=poi.longitude,
            radius=poi.radius,
            address=poi.address,
            destination_latitude=poi.destination_latitude,
            destination_longitude=poi.destination_longitude,
            destination_radius=poi.destination_radius,
            destination_address=poi.destination_address,
            is_active=poi.is_active,
            created_at=poi.created_at,
            updated_at=poi.updated_at,
            armed_trackers=armed_tracker_ids
        ))
    
    return result


@app.get("/api/v1/pois/{poi_id}", response_model=POIWithArmedStatus)
def get_poi(
    poi_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific POI"""
    poi = db.query(POI).filter(
        POI.id == poi_id,
        POI.user_id == str(current_user.id)
    ).first()
    
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    
    # Get armed trackers
    armed_links = db.query(POITrackerLink).filter(
        POITrackerLink.poi_id == poi.id,
        POITrackerLink.is_armed == True
    ).all()
    
    armed_tracker_ids = [str(link.tracker_id) for link in armed_links]
    
    return POIWithArmedStatus(
        id=str(poi.id),
        user_id=str(poi.user_id),
        name=poi.name,
        description=poi.description,
        poi_type=poi.poi_type,
        latitude=poi.latitude,
        longitude=poi.longitude,
        radius=poi.radius,
        address=poi.address,
        destination_latitude=poi.destination_latitude,
        destination_longitude=poi.destination_longitude,
        destination_radius=poi.destination_radius,
        destination_address=poi.destination_address,
        is_active=poi.is_active,
        created_at=poi.created_at,
        updated_at=poi.updated_at,
        armed_trackers=armed_tracker_ids
    )


@app.put("/api/v1/pois/{poi_id}", response_model=POIResponse)
def update_poi(
    poi_id: str,
    poi_update: POIUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a POI"""
    poi = db.query(POI).filter(
        POI.id == poi_id,
        POI.user_id == str(current_user.id)
    ).first()
    
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    
    # Update fields if provided
    if poi_update.name is not None:
        poi.name = poi_update.name
    if poi_update.description is not None:
        poi.description = poi_update.description
    if poi_update.radius is not None:
        poi.radius = poi_update.radius
    if poi_update.destination_radius is not None:
        poi.destination_radius = poi_update.destination_radius
    if poi_update.is_active is not None:
        poi.is_active = poi_update.is_active
    
    db.commit()
    db.refresh(poi)
    
    return POIResponse(
        id=str(poi.id),
        user_id=str(poi.user_id),
        name=poi.name,
        description=poi.description,
        poi_type=poi.poi_type,
        latitude=poi.latitude,
        longitude=poi.longitude,
        radius=poi.radius,
        address=poi.address,
        destination_latitude=poi.destination_latitude,
        destination_longitude=poi.destination_longitude,
        destination_radius=poi.destination_radius,
        destination_address=poi.destination_address,
        is_active=poi.is_active,
        created_at=poi.created_at,
        updated_at=poi.updated_at
    )


@app.delete("/api/v1/pois/{poi_id}")
def delete_poi(
    poi_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a POI"""
    poi = db.query(POI).filter(
        POI.id == poi_id,
        POI.user_id == str(current_user.id)
    ).first()
    
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    
    # Delete related links and alerts first
    db.query(POITrackerLink).filter(POITrackerLink.poi_id == poi_id).delete()
    db.query(GeofenceAlert).filter(GeofenceAlert.poi_id == poi_id).delete()
    
    db.delete(poi)
    db.commit()
    
    return {"message": "POI deleted successfully"}


# ==================== POI-Tracker ARM/DISARM ====================

@app.post("/api/v1/pois/{poi_id}/arm/{tracker_id}")
def arm_poi_to_tracker(
    poi_id: str,
    tracker_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ARM a POI to a tracker (enable geofence monitoring)"""
    # Verify POI belongs to user
    poi = db.query(POI).filter(
        POI.id == poi_id,
        POI.user_id == str(current_user.id)
    ).first()
    
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    
    # Verify tracker belongs to user
    tracker = db.query(BLETag).filter(
        BLETag.id == tracker_id,
        BLETag.user_id == str(current_user.id)
    ).first()
    
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")
    
    # Get tracker's current GPS position to set initial state
    initial_state = GeofenceState.UNKNOWN
    try:
        # Fetch vehicle location from MZone API
        user_imeis = [tracker.imei]
        vehicles = mzone_service.get_vehicles_with_locations(user_imeis)
        
        if vehicles and len(vehicles) > 0:
            vehicle = vehicles[0]
            last_position = vehicle.get('lastKnownPosition')
            
            if last_position:
                current_lat = last_position.get('latitude')
                current_lon = last_position.get('longitude')
                
                if current_lat is not None and current_lon is not None:
                    # Determine if tracker is currently inside or outside POI
                    is_inside = GeofenceService.is_inside_geofence(
                        current_lat, current_lon,
                        poi.latitude, poi.longitude,
                        poi.radius
                    )
                    initial_state = GeofenceState.INSIDE if is_inside else GeofenceState.OUTSIDE
                    logger.info(f"Armed POI '{poi.name}' to tracker {tracker.imei}: initial state = {initial_state.value}")
    except Exception as e:
        logger.warning(f"Could not determine initial state for POI arming: {str(e)}")
        # Continue with UNKNOWN state
    
    # Check if link already exists
    existing_link = db.query(POITrackerLink).filter(
        POITrackerLink.poi_id == poi_id,
        POITrackerLink.tracker_id == tracker_id
    ).first()
    
    if existing_link:
        # Re-arm if it was disarmed - reset state based on current position
        if not existing_link.is_armed:
            existing_link.is_armed = True
            existing_link.armed_at = datetime.utcnow()
            existing_link.disarmed_at = None
            existing_link.last_known_state = initial_state
            db.commit()
            return {"message": f"POI re-armed to tracker (state: {initial_state.value})"}
        else:
            return {"message": "POI already armed to tracker"}
    
    # Create new link with determined initial state
    link = POITrackerLink(
        poi_id=poi_id,
        tracker_id=tracker_id,
        is_armed=True,
        last_known_state=initial_state
    )
    
    db.add(link)
    db.commit()
    
    return {"message": f"POI armed to tracker successfully (state: {initial_state.value})"}


@app.post("/api/v1/pois/{poi_id}/disarm/{tracker_id}")
def disarm_poi_from_tracker(
    poi_id: str,
    tracker_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DISARM a POI from a tracker (disable geofence monitoring)"""
    # Verify POI belongs to user
    poi = db.query(POI).filter(
        POI.id == poi_id,
        POI.user_id == str(current_user.id)
    ).first()
    
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    
    # Find the link
    link = db.query(POITrackerLink).filter(
        POITrackerLink.poi_id == poi_id,
        POITrackerLink.tracker_id == tracker_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="POI is not armed to this tracker")
    
    # Disarm
    link.is_armed = False
    link.disarmed_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "POI disarmed from tracker successfully"}


# ==================== Geofence Alerts ====================

@app.get("/api/v1/alerts", response_model=AlertsListResponse)
def get_alerts(
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get geofence alerts for the current user"""
    alerts, total, unread_count = GeofenceService.get_user_alerts(
        db, str(current_user.id), limit, offset, unread_only
    )
    
    # Format alerts with POI and tracker names
    formatted_alerts = []
    for alert in alerts:
        poi = db.query(POI).filter(POI.id == alert.poi_id).first()
        tracker = db.query(BLETag).filter(BLETag.id == alert.tracker_id).first()
        
        # Get tracker display name (priority: description > device_name > IMEI last 4)
        if tracker:
            if tracker.description:
                tracker_name = tracker.description
            elif tracker.device_name:
                tracker_name = tracker.device_name
            elif tracker.imei:
                tracker_name = f"GPS Tracker ({tracker.imei[-4:]})"
            else:
                tracker_name = "GPS Tracker"
        else:
            tracker_name = None
        
        formatted_alerts.append(GeofenceAlertResponse(
            id=str(alert.id),
            poi_id=str(alert.poi_id),
            tracker_id=str(alert.tracker_id),
            user_id=str(alert.user_id),
            event_type=alert.event_type,
            latitude=alert.latitude,
            longitude=alert.longitude,
            is_read=alert.is_read,
            created_at=alert.created_at,
            poi_name=poi.name if poi else None,
            tracker_name=tracker_name
        ))
    
    return AlertsListResponse(
        alerts=formatted_alerts,
        total=total,
        unread_count=unread_count
    )


@app.post("/api/v1/alerts/{alert_id}/mark-read")
def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a specific alert as read"""
    count = GeofenceService.mark_alerts_read(db, [alert_id], str(current_user.id))
    
    if count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert marked as read"}


@app.post("/api/v1/alerts/mark-all-read")
def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all alerts as read for the current user"""
    count = GeofenceService.mark_all_alerts_read(db, str(current_user.id))
    
    return {"message": f"{count} alerts marked as read"}


# ==================== Postcode Search ====================

@app.post("/api/v1/search/postcode", response_model=PostcodeSearchResponse)
async def search_postcode(request: PostcodeSearchRequest):
    """
    Search for a UK postcode using postcodes.io (free UK postcode API)
    Can be upgraded to Google Maps Geocoding API by setting GOOGLE_MAPS_API_KEY
    """
    import httpx
    import os
    
    try:
        # Use postcodes.io as primary option (free, no API key needed)
        postcode = request.postcode.replace(" ", "").upper()
        
        logger.info(f"Searching for postcode: {postcode}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.postcodes.io/postcodes/{postcode}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})
                
                # Format address from postcodes.io data
                address_parts = []
                if result.get('postcode'):
                    address_parts.append(result.get('postcode'))
                if result.get('admin_district'):
                    address_parts.append(result.get('admin_district'))
                if result.get('region'):
                    address_parts.append(result.get('region'))
                address_parts.append('UK')
                
                formatted_address = ', '.join(address_parts)
                
                logger.info(f"Found postcode: {formatted_address}")
                
                return PostcodeSearchResponse(
                    latitude=result.get("latitude"),
                    longitude=result.get("longitude"),
                    address=formatted_address
                )
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="Postcode not found")
            else:
                raise HTTPException(status_code=500, detail=f"Postcode API error: {response.status_code}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Postcode search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching postcode: {str(e)}")


@app.post("/api/v1/test/mock-location", tags=["Testing"])
async def mock_location_test(
    request: MockLocationTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mock test endpoint for geofence notifications.
    Simulates a tracker location update to test geofence alerts and email notifications.
    
    Returns details of any alerts triggered, including whether emails were sent.
    """
    try:
        # Verify tracker exists and belongs to user
        tracker = db.query(BLETag).filter(
            BLETag.id == request.tracker_id,
            BLETag.user_id == current_user.id
        ).first()
        
        if not tracker:
            raise HTTPException(status_code=404, detail="Tracker not found")
        
        # Call geofence service to check all armed POIs
        alerts = GeofenceService.check_geofences_for_tracker(
            db,
            request.tracker_id,
            request.latitude,
            request.longitude,
            str(current_user.id)
        )
        
        # Get POI details for each alert
        alert_details = []
        for alert in alerts:
            poi = db.query(POI).filter(POI.id == alert.poi_id).first()
            alert_details.append({
                "alert_id": str(alert.id),
                "poi_id": str(alert.poi_id),
                "poi_name": poi.name if poi else "Unknown",
                "poi_type": poi.poi_type if poi else "Unknown",
                "event_type": alert.event_type.value,
                "latitude": alert.latitude,
                "longitude": alert.longitude,
                "created_at": alert.created_at.isoformat()
            })
        
        # Check if user has email alerts enabled
        user = db.query(User).filter(User.id == current_user.id).first()
        email_enabled = user.email_alerts_enabled if user else False
        
        return {
            "success": True,
            "tracker_id": request.tracker_id,
            "test_location": {
                "latitude": request.latitude,
                "longitude": request.longitude
            },
            "alerts_triggered": len(alerts),
            "email_alerts_enabled": email_enabled,
            "message": f"Test completed. {len(alerts)} alert(s) generated. Email notifications {'sent' if email_enabled and alerts else 'not sent (email alerts disabled or no alerts triggered)'}.",
            "alerts": alert_details,
            "mailhog_url": "http://localhost:8025",
            "instructions": "Check MailHog at http://localhost:8025 to see email notifications if alerts were triggered and email_alerts_enabled is true."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mock location test error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error running mock test: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
