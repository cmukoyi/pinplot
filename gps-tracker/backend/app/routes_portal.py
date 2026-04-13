"""
Customer portal API endpoints — auth and portal-user management.

Routes are mounted at /api/portal (separate from /api/v1 user routes and
/api/admin admin routes).  Each PortalUser is scoped to a UserGroup (tenant).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
import jwt
import os
import logging

from app.database import get_db
from app.models import UserGroup, PortalUser, Building, Floor, IndoorGateway
from app.admin_auth import hash_password, verify_password

router = APIRouter(prefix="/api/portal", tags=["portal"])
logger = logging.getLogger(__name__)

PORTAL_SECRET_KEY = os.getenv("PORTAL_SECRET_KEY", os.getenv("ADMIN_SECRET_KEY", "portal-secret-key-change-me"))
PORTAL_ALGORITHM = "HS256"
PORTAL_TOKEN_EXPIRE_HOURS = 12


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PortalLoginRequest(BaseModel):
    email: str
    password: str


class PortalUserOut(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_group_admin: bool

    class Config:
        from_attributes = True


class UserGroupOut(BaseModel):
    id: UUID
    name: str
    slug: str

    class Config:
        from_attributes = True


class PortalTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    portal_user: PortalUserOut
    usergroup: UserGroupOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_portal_token(portal_user_id: str, usergroup_id: str) -> str:
    payload = {
        "portal_user_id": portal_user_id,
        "usergroup_id":   usergroup_id,
        "type":           "portal",
        "exp":            datetime.utcnow() + timedelta(hours=PORTAL_TOKEN_EXPIRE_HOURS),
        "iat":            datetime.utcnow(),
    }
    return jwt.encode(payload, PORTAL_SECRET_KEY, algorithm=PORTAL_ALGORITHM)


def _decode_portal_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, PORTAL_SECRET_KEY, algorithms=[PORTAL_ALGORITHM])
        if payload.get("type") != "portal":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_portal_user_from_request(request: Request, db: Session) -> PortalUser:
    """Dependency: extract and validate portal JWT, return PortalUser."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Missing or invalid authorization header")
    token = auth[7:]
    payload = _decode_portal_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token")
    user = db.query(PortalUser).filter(
        PortalUser.id == payload["portal_user_id"],
        PortalUser.is_active == True,
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Portal user not found or inactive")
    return user


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=PortalTokenResponse)
def portal_login(data: PortalLoginRequest, db: Session = Depends(get_db)):
    """Log in as a portal user. Returns a JWT scoped to the user's UserGroup."""
    user = db.query(PortalUser).filter(
        PortalUser.email == data.email.lower().strip(),
        PortalUser.is_active == True,
    ).first()

    if not user or not verify_password(user.hashed_password, data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password")

    group = db.query(UserGroup).filter(
        UserGroup.id == user.usergroup_id,
        UserGroup.is_active == True,
    ).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User group is inactive or not found")

    token = _create_portal_token(str(user.id), str(user.usergroup_id))
    return PortalTokenResponse(
        access_token=token,
        portal_user=PortalUserOut.model_validate(user),
        usergroup=UserGroupOut.model_validate(group),
    )


@router.get("/me")
def portal_me(
    request: Request,
    db: Session = Depends(get_db),
):
    """Return the logged-in portal user's profile + usergroup."""
    user = get_portal_user_from_request(request, db)
    group = db.query(UserGroup).filter(UserGroup.id == user.usergroup_id).first()
    return {
        "portal_user": PortalUserOut.model_validate(user),
        "usergroup":   UserGroupOut.model_validate(group) if group else None,
    }


# ---------------------------------------------------------------------------
# Portal user management (group admin only)
# ---------------------------------------------------------------------------

class PortalUserCreate(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class PortalUserCreateResponse(BaseModel):
    portal_user: PortalUserOut
    temp_password: str


@router.get("/users", response_model=List[PortalUserOut])
def list_portal_users(
    request: Request,
    db: Session = Depends(get_db),
):
    """List all portal users in the caller's UserGroup."""
    me = get_portal_user_from_request(request, db)
    users = db.query(PortalUser).filter(
        PortalUser.usergroup_id == me.usergroup_id,
    ).order_by(PortalUser.created_at).all()
    return [PortalUserOut.model_validate(u) for u in users]


@router.post("/users", response_model=PortalUserCreateResponse)
def create_portal_user(
    data: PortalUserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new portal user in the same UserGroup (group admin only)."""
    me = get_portal_user_from_request(request, db)
    if not me.is_group_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only group admins can create users")

    email = data.email.lower().strip()
    if db.query(PortalUser).filter(PortalUser.email == email).first():
        raise HTTPException(status_code=400, detail="A portal user with that email already exists")

    import secrets as _secrets
    import uuid as _uuid
    temp_password = _secrets.token_urlsafe(12)

    new_user = PortalUser(
        id=str(_uuid.uuid4()),
        usergroup_id=me.usergroup_id,
        email=email,
        hashed_password=hash_password(temp_password),
        first_name=data.first_name or None,
        last_name=data.last_name or None,
        is_active=True,
        is_group_admin=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return PortalUserCreateResponse(
        portal_user=PortalUserOut.model_validate(new_user),
        temp_password=temp_password,
    )


# ---------------------------------------------------------------------------
# Buildings — read-only for portal users
# ---------------------------------------------------------------------------

class RoomOut(BaseModel):
    id: str
    floor_id: str
    name: str
    x: float
    y: float
    w: float
    h: float
    class Config: from_attributes = True

class GatewayOut(BaseModel):
    id: str
    floor_id: str
    receiver_id: str
    label: Optional[str]
    x: float
    y: float
    class Config: from_attributes = True

class FloorOut(BaseModel):
    id: str
    building_id: str
    label: str
    floor_order: int
    floor_plan: Optional[str]
    map_w: int
    map_h: int
    gateways: List[GatewayOut] = []
    rooms: List[RoomOut] = []
    class Config: from_attributes = True

class BuildingOut(BaseModel):
    id: str
    usergroup_id: str
    name: str
    mqtt_url: Optional[str]
    mqtt_topic: str
    floors: List[FloorOut] = []
    class Config: from_attributes = True


@router.get("/buildings", response_model=List[BuildingOut])
def list_buildings(request: Request, db: Session = Depends(get_db)):
    """Return all buildings for the calling user's UserGroup."""
    me = get_portal_user_from_request(request, db)
    buildings = (
        db.query(Building)
        .filter(Building.usergroup_id == me.usergroup_id)
        .order_by(Building.created_at)
        .all()
    )
    return [BuildingOut.model_validate(b) for b in buildings]


@router.get("/buildings/{building_id}", response_model=BuildingOut)
def get_building(building_id: str, request: Request, db: Session = Depends(get_db)):
    """Return a single building with all floors, gateways, and rooms."""
    me = get_portal_user_from_request(request, db)
    bldg = db.query(Building).filter(
        Building.id == building_id,
        Building.usergroup_id == me.usergroup_id,
    ).first()
    if not bldg:
        raise HTTPException(status_code=404, detail="Building not found")
    return BuildingOut.model_validate(bldg)


# ---------------------------------------------------------------------------
# Gateway lookup — used by the mqtt-bridge to fetch positions without a user token
# ---------------------------------------------------------------------------

BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY", "bridge-key-change-me")


@router.get("/gateways")
def list_all_gateways(request: Request, db: Session = Depends(get_db)):
    """Return a flat map of receiverId → {x, y, floor_id, floor_label, building_id}.

    Authenticated with the BRIDGE_API_KEY header (X-Bridge-Key) so the
    mqtt-bridge container can call it without a portal JWT.
    """
    key = request.headers.get("X-Bridge-Key", "")
    if key != BRIDGE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid bridge API key")

    gateways = (
        db.query(IndoorGateway)
        .join(Floor, Floor.id == IndoorGateway.floor_id)
        .all()
    )
    result = {}
    for gw in gateways:
        result[gw.receiver_id] = {
            "x":           gw.x,
            "y":           gw.y,
            "label":       gw.label,
            "floor_id":    str(gw.floor_id),
            "floor_label": gw.floor.label,
            "building_id": str(gw.floor.building_id),
        }
    return result
