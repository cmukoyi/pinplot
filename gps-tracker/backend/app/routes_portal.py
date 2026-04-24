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
from app.models import UserGroup, PortalUser, Building, Floor, IndoorGateway, BLETag, User
from app.models_admin import TagPackage
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
    id: UUID
    floor_id: UUID
    name: str
    x: float
    y: float
    w: float
    h: float
    class Config: from_attributes = True

class GatewayOut(BaseModel):
    id: UUID
    floor_id: UUID
    receiver_id: str
    label: Optional[str]
    x: float
    y: float
    class Config: from_attributes = True

class FloorOut(BaseModel):
    id: UUID
    building_id: UUID
    label: str
    floor_order: int
    floor_plan: Optional[str]
    map_w: int
    map_h: int
    gateways: List[GatewayOut] = []
    rooms: List[RoomOut] = []
    class Config: from_attributes = True

class BuildingOut(BaseModel):
    id: UUID
    usergroup_id: UUID
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


# ---------------------------------------------------------------------------
# Settings — group admin can configure email domain auto-assignment
# ---------------------------------------------------------------------------

class GroupSettingsOut(BaseModel):
    id: UUID
    name: str
    slug: str
    email_domain: Optional[str]

    class Config:
        from_attributes = True


class GroupSettingsUpdate(BaseModel):
    email_domain: Optional[str] = None   # set to "" or null to clear


@router.get("/settings", response_model=GroupSettingsOut)
def get_settings(request: Request, db: Session = Depends(get_db)):
    """Return the current UserGroup settings for the logged-in portal user."""
    me = get_portal_user_from_request(request, db)
    group = db.query(UserGroup).filter(UserGroup.id == me.usergroup_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")
    return GroupSettingsOut.model_validate(group)


@router.put("/settings", response_model=GroupSettingsOut)
def update_settings(
    data: GroupSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update UserGroup settings (group admin only)."""
    me = get_portal_user_from_request(request, db)
    if not me.is_group_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only group admins can update settings")

    group = db.query(UserGroup).filter(UserGroup.id == me.usergroup_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # Normalise domain: strip whitespace, lowercase, strip leading "@" if present
    domain = (data.email_domain or "").strip().lower().lstrip("@") or None

    # Ensure no other group is already using this domain
    if domain:
        conflict = db.query(UserGroup).filter(
            UserGroup.email_domain == domain,
            UserGroup.id != group.id,
        ).first()
        if conflict:
            raise HTTPException(
                status_code=400,
                detail=f"Domain '{domain}' is already claimed by another group",
            )

    group.email_domain = domain
    db.commit()
    db.refresh(group)
    return GroupSettingsOut.model_validate(group)


# ---------------------------------------------------------------------------
# Tags — all BLE tags belonging to mobile-app users whose email domain
#         matches the group's configured email_domain
# ---------------------------------------------------------------------------

class PortalTagOut(BaseModel):
    id: UUID
    imei: str
    device_name: Optional[str]
    device_model: Optional[str]
    description: Optional[str]
    tag_type: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    latitude: Optional[str]
    longitude: Optional[str]
    location_description: Optional[str]
    battery_level: Optional[int]
    owner_email: str
    # Package / subscription fields
    package_id: Optional[str] = None
    package_name: Optional[str] = None
    added_at: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    days_remaining: Optional[int] = None  # None = no package; negative = expired

    class Config:
        from_attributes = True


@router.get("/tags", response_model=List[PortalTagOut])
def list_group_tags(request: Request, db: Session = Depends(get_db)):
    """Return all BLE tags belonging to mobile-app users whose email domain
    matches the group's configured email_domain.

    Returns an empty list (not an error) when no domain is configured yet.
    """
    me = get_portal_user_from_request(request, db)
    group = db.query(UserGroup).filter(UserGroup.id == me.usergroup_id).first()
    if not group or not group.email_domain:
        return []

    domain = group.email_domain.lower()

    tags = (
        db.query(BLETag, User.email)
        .join(User, User.id == BLETag.user_id)
        .filter(
            User.email.ilike(f"%@{domain}"),
            BLETag.is_active == True,
        )
        .order_by(BLETag.added_at.desc())
        .all()
    )

    # Build package lookup cache for this batch
    pkg_ids = {t.package_id for t, _ in tags if t.package_id}
    pkg_map: dict = {}
    if pkg_ids:
        for p in db.query(TagPackage).filter(TagPackage.id.in_(pkg_ids)).all():
            pkg_map[str(p.id)] = p

    result = []
    for tag, owner_email in tags:
        pkg = pkg_map.get(str(tag.package_id)) if tag.package_id else None
        days_remaining = None
        if tag.expiry_date:
            days_remaining = (tag.expiry_date.replace(tzinfo=None) - datetime.utcnow()).days
        result.append(PortalTagOut(
            id=tag.id,
            imei=tag.imei,
            device_name=tag.device_name,
            device_model=tag.device_model,
            description=tag.description,
            tag_type=tag.tag_type,
            is_active=tag.is_active,
            last_seen=tag.last_seen,
            latitude=tag.latitude,
            longitude=tag.longitude,
            location_description=tag.location_description,
            battery_level=tag.battery_level,
            owner_email=owner_email,
            package_id=str(tag.package_id) if tag.package_id else None,
            package_name=pkg.name if pkg else None,
            added_at=tag.added_at,
            expiry_date=tag.expiry_date,
            days_remaining=days_remaining,
        ))
    return result


# ---------------------------------------------------------------------------
# Packages — list active packages available for portal to assign to tags
# ---------------------------------------------------------------------------

class PackageOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    validity_days: int
    is_default: bool

    class Config:
        from_attributes = True


@router.get("/packages", response_model=List[PackageOut])
def list_active_packages(request: Request, db: Session = Depends(get_db)):
    """Return all active tag packages for the Add Tag dropdown."""
    get_portal_user_from_request(request, db)  # auth only
    return db.query(TagPackage).filter(TagPackage.is_active == True).order_by(TagPackage.validity_days).all()


# ---------------------------------------------------------------------------
# Mobile users — list mobile-app Users in the group's email domain
# ---------------------------------------------------------------------------

class MobileUserOut(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]

    class Config:
        from_attributes = True


@router.get("/mobile-users", response_model=List[MobileUserOut])
def list_mobile_users(request: Request, db: Session = Depends(get_db)):
    """Return all active mobile-app Users whose email domain matches the group's
    configured email_domain. Used to populate the assign-tag dropdown."""
    me = get_portal_user_from_request(request, db)
    group = db.query(UserGroup).filter(UserGroup.id == me.usergroup_id).first()
    if not group or not group.email_domain:
        return []
    domain = group.email_domain.lower()
    users = (
        db.query(User)
        .filter(User.email.ilike(f"%@{domain}"), User.is_active == True)
        .order_by(User.email)
        .all()
    )
    return [MobileUserOut(id=u.id, email=u.email, first_name=u.first_name, last_name=u.last_name)
            for u in users]


# ---------------------------------------------------------------------------
# Tag management — create and reassign tags from the portal
# ---------------------------------------------------------------------------

class PortalTagCreate(BaseModel):
    imei: str
    description: Optional[str] = None
    tag_type: Optional[str] = "scope"
    user_id: UUID
    package_id: UUID  # mandatory — must select a package when adding a tag


class PortalTagAssign(BaseModel):
    user_id: UUID


class PortalTagDelete(BaseModel):
    tag_ids: List[str]


def _build_tag_out(tag: BLETag, owner_email: str, db: Optional[Session] = None) -> PortalTagOut:
    pkg = None
    if tag.package_id and db:
        pkg = db.query(TagPackage).filter(TagPackage.id == str(tag.package_id)).first()
    days_remaining = None
    if tag.expiry_date:
        days_remaining = (tag.expiry_date.replace(tzinfo=None) - datetime.utcnow()).days
    return PortalTagOut(
        id=tag.id,
        imei=tag.imei,
        device_name=tag.device_name,
        device_model=tag.device_model,
        description=tag.description,
        tag_type=tag.tag_type,
        is_active=tag.is_active,
        last_seen=tag.last_seen,
        latitude=tag.latitude,
        longitude=tag.longitude,
        location_description=tag.location_description,
        battery_level=tag.battery_level,
        owner_email=owner_email,
        package_id=str(tag.package_id) if tag.package_id else None,
        package_name=pkg.name if pkg else None,
        added_at=tag.added_at,
        expiry_date=tag.expiry_date,
        days_remaining=days_remaining,
    )


def _get_group_and_assert_domain(me: PortalUser, db: Session) -> UserGroup:
    group = db.query(UserGroup).filter(UserGroup.id == me.usergroup_id).first()
    if not group or not group.email_domain:
        raise HTTPException(status_code=400, detail="Configure a domain in Settings before managing tags")
    return group


def _assert_user_in_domain(user: User, domain: str) -> None:
    if not user or not user.email.lower().endswith(f"@{domain.lower()}"):
        raise HTTPException(status_code=403, detail="User does not belong to this group's domain")


class PortalTagUpdate(BaseModel):
    description: Optional[str] = None
    tag_type: Optional[str] = None
    user_id: Optional[str] = None


@router.put("/tags/{tag_id}", response_model=PortalTagOut)
def update_tag(tag_id: str, data: PortalTagUpdate, request: Request, db: Session = Depends(get_db)):
    """Update a BLE tag's description, type, or assigned user (group admin only)."""
    me = get_portal_user_from_request(request, db)
    if not me.is_group_admin:
        raise HTTPException(status_code=403, detail="Only group admins can edit tags")
    group = _get_group_and_assert_domain(me, db)

    tag = (
        db.query(BLETag)
        .join(User, User.id == BLETag.user_id)
        .filter(BLETag.id == tag_id, User.email.ilike(f"%@{group.email_domain.lower()}"))
        .first()
    )
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found in your group")

    if data.description is not None:
        tag.description = data.description or None
    if data.tag_type is not None:
        tag.tag_type = data.tag_type
    if data.user_id is not None:
        target_user = db.query(User).filter(User.id == str(data.user_id)).first()
        _assert_user_in_domain(target_user, group.email_domain)
        tag.user_id = str(data.user_id)

    db.commit()
    db.refresh(tag)
    owner = db.query(User).filter(User.id == tag.user_id).first()
    return _build_tag_out(tag, owner.email if owner else "", db)


@router.post("/tags", response_model=PortalTagOut, status_code=201)
def create_tag(data: PortalTagCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new BLE tag and assign it directly to a mobile-app user (group admin only)."""
    me = get_portal_user_from_request(request, db)
    if not me.is_group_admin:
        raise HTTPException(status_code=403, detail="Only group admins can add tags")
    group = _get_group_and_assert_domain(me, db)

    target_user = db.query(User).filter(User.id == str(data.user_id)).first()
    _assert_user_in_domain(target_user, group.email_domain)

    pkg = db.query(TagPackage).filter(TagPackage.id == str(data.package_id), TagPackage.is_active == True).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found or inactive")

    imei = data.imei.strip()
    if db.query(BLETag).filter(BLETag.imei == imei).first():
        raise HTTPException(status_code=409, detail=f"Tag with IMEI '{imei}' already exists")

    now = datetime.utcnow()
    tag = BLETag(
        user_id=str(data.user_id),
        imei=imei,
        description=data.description,
        tag_type=data.tag_type or "scope",
        is_active=True,
        package_id=str(data.package_id),
        expiry_date=now + timedelta(days=pkg.validity_days),
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _build_tag_out(tag, target_user.email, db)


@router.put("/tags/{tag_id}/assign", response_model=PortalTagOut)
def assign_tag(tag_id: str, data: PortalTagAssign, request: Request, db: Session = Depends(get_db)):
    """Reassign an existing BLE tag to a different mobile-app user (group admin only)."""
    me = get_portal_user_from_request(request, db)
    if not me.is_group_admin:
        raise HTTPException(status_code=403, detail="Only group admins can assign tags")
    group = _get_group_and_assert_domain(me, db)

    # Tag must belong to a user already in this group's domain
    tag = (
        db.query(BLETag)
        .join(User, User.id == BLETag.user_id)
        .filter(BLETag.id == tag_id, User.email.ilike(f"%@{group.email_domain.lower()}"))
        .first()
    )
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found in your group")

    target_user = db.query(User).filter(User.id == str(data.user_id)).first()
    _assert_user_in_domain(target_user, group.email_domain)

    tag.user_id = str(data.user_id)
    db.commit()
    db.refresh(tag)
    return _build_tag_out(tag, target_user.email, db)


@router.delete("/tags", status_code=204)
def delete_tags(data: PortalTagDelete, request: Request, db: Session = Depends(get_db)):
    """Permanently delete one or more BLE tags (group admin only).
    Tags must belong to a user in the group's configured email domain."""
    me = get_portal_user_from_request(request, db)
    if not me.is_group_admin:
        raise HTTPException(status_code=403, detail="Only group admins can delete tags")
    group = _get_group_and_assert_domain(me, db)

    for tag_id in data.tag_ids:
        tag = (
            db.query(BLETag)
            .join(User, User.id == BLETag.user_id)
            .filter(BLETag.id == tag_id, User.email.ilike(f"%@{group.email_domain.lower()}"))
            .first()
        )
        if tag:
            db.delete(tag)

    db.commit()


# ---------------------------------------------------------------------------
# Trips — portal-scoped proxy to MZone / TrackSolid
# ---------------------------------------------------------------------------

class PortalTripsRequest(BaseModel):
    vehicleId: str
    startDate: str   # ISO 8601 UTC e.g. "2025-10-01T07:00:00Z"
    endDate: str     # ISO 8601 UTC e.g. "2025-10-01T18:00:59Z"


@router.post("/trips")
async def portal_get_trips(
    data: PortalTripsRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Fetch trips for a BLE tag within a date range.
    Routes to TrackSolid getPointList or MZone Trips API depending on tag_type.
    Auth: portal JWT (PortalUser scoped to a UserGroup)."""
    me = get_portal_user_from_request(request, db)
    group = db.query(UserGroup).filter(UserGroup.id == me.usergroup_id).first()
    if not group or not group.email_domain:
        return {"success": False, "error": "Group has no configured domain", "trips": []}

    # Verify the tag belongs to this group's domain
    tag = (
        db.query(BLETag)
        .join(User, User.id == BLETag.user_id)
        .filter(
            BLETag.id == data.vehicleId,
            BLETag.is_active == True,
            User.email.ilike(f"%@{group.email_domain.lower()}"),
        )
        .first()
    )
    if not tag:
        return {"success": False, "error": "Tag not found or not in your group", "trips": []}

    print(f"📱 PORTAL TRIPS REQUEST — group={group.slug} tag={tag.imei} {data.startDate}→{data.endDate}")

    # ── TrackSolid ────────────────────────────────────────────────────────────
    if (tag.tag_type or "").lower() == "tracksolid":
        from app.services.device_providers.tracksolid_provider import fetch_tracksolid_journey_points
        from datetime import datetime as _dt

        def _to_ts(s: str) -> str:
            return s.replace("T", " ").replace("Z", "").split(".")[0][:19]

        ts_start = _to_ts(data.startDate)
        ts_end   = _to_ts(data.endDate)
        print(f"🔵 TrackSolid journey: IMEI={tag.imei} {ts_start} → {ts_end}")

        track_data = await fetch_tracksolid_journey_points(tag.imei, ts_start, ts_end)
        if not track_data or not (track_data.get("gpsPointStrList") or []):
            return {"success": True, "count": 0, "trips": []}

        try:
            t0 = _dt.strptime(track_data["startDate"], "%Y-%m-%d %H:%M:%S")
            t1 = _dt.strptime(track_data["endDate"],   "%Y-%m-%d %H:%M:%S")
            duration_secs = int((t1 - t0).total_seconds())
        except Exception:
            duration_secs = 0

        try:
            distance_mi = float(track_data.get("totalMileage") or 0)
        except (ValueError, TypeError):
            distance_mi = 0.0

        trip_id = (
            f"tracksolid__{tag.imei}"
            f"__{ts_start.replace(' ', 'T')}"
            f"__{ts_end.replace(' ', 'T')}"
        )
        synthetic_trip = {
            "id": trip_id,
            "vehicle_Id": str(tag.id),
            "vehicle_Description": track_data.get("deviceName") or tag.description or tag.imei,
            "driver_Description": None,
            "driverKeyCode": None,
            "distance": distance_mi,
            "duration": duration_secs,
            "startUtcTimestamp": track_data["startDate"].replace(" ", "T") + "Z",
            "endUtcTimestamp":   track_data["endDate"].replace(" ", "T") + "Z",
            "startLocationDescription": track_data.get("startAddress"),
            "endLocationDescription":   track_data.get("endAddress"),
        }
        print(f"✅ TrackSolid: {len(track_data['gpsPointStrList'])} pts, {distance_mi:.1f} mi, {duration_secs}s")
        return {"success": True, "count": 1, "trips": [synthetic_trip]}

    # ── MZone ─────────────────────────────────────────────────────────────────
    from app.services.mzone_service import mzone_service

    mzone_vehicle_id = tag.mzone_vehicle_id
    if not mzone_vehicle_id:
        print(f"⚠️  No cached MZone vehicle_Id, performing IMEI lookup…")
        vehicles_data = mzone_service.get_all_vehicles()
        if not vehicles_data:
            return {"success": False, "error": "Failed to fetch vehicles from MZone", "trips": []}
        for vehicle in vehicles_data.get("value", []):
            if vehicle.get("registration") == tag.imei or vehicle.get("unit_Description") == tag.imei:
                mzone_vehicle_id = vehicle.get("id")
                tag.mzone_vehicle_id = mzone_vehicle_id
                db.commit()
                print(f"✅ Cached MZone vehicle_Id={mzone_vehicle_id}")
                break
        if not mzone_vehicle_id:
            return {"success": False, "error": "Vehicle not found in MZone system", "trips": []}
    else:
        print(f"✅ Using cached MZone vehicle_Id (fast path)")

    trips_data = mzone_service.get_trips(
        vehicle_id=mzone_vehicle_id,
        start_date=data.startDate,
        end_date=data.endDate,
    )
    if not trips_data:
        return {"success": False, "error": "Failed to fetch trips from MZone", "trips": []}

    trips = trips_data.get("value", [])
    print(f"✅ MZone: {len(trips)} trips returned")
    return {"success": True, "count": len(trips), "trips": trips}


@router.get("/trips/{trip_id}/events")
async def portal_get_trip_events(
    trip_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Fetch waypoints for a specific trip. Routes to TrackSolid or MZone.
    Auth: portal JWT."""
    get_portal_user_from_request(request, db)  # auth only — trip_id encodes all needed info

    # ── TrackSolid compound ID: tracksolid__{imei}__{start}__{end} ────────────
    if trip_id.startswith("tracksolid__"):
        from app.services.device_providers.tracksolid_provider import fetch_tracksolid_journey_points

        parts = trip_id.split("__")
        if len(parts) != 4:
            return {"success": False, "error": "Invalid TrackSolid trip ID format", "events": []}

        _, imei, ts_start_raw, ts_end_raw = parts
        ts_start = ts_start_raw.replace("T", " ")
        ts_end   = ts_end_raw.replace("T", " ")
        print(f"🔵 TrackSolid events: IMEI={imei} {ts_start} → {ts_end}")

        track_data = await fetch_tracksolid_journey_points(imei, ts_start, ts_end)
        if not track_data:
            return {"success": True, "count": 0, "events": []}

        points_raw = track_data.get("gpsPointStrList") or []
        events = []
        for idx, point_str in enumerate(points_raw):
            try:
                p = point_str.split("|")
                if len(p) < 10:
                    continue
                lat = float(p[8])
                lng = float(p[9])
                if lat == 0.0 and lng == 0.0:
                    continue
                events.append({
                    "id": str(idx),
                    "utcTimestamp": p[7].replace(" ", "T") + "Z",
                    "latitude":  lat,
                    "longitude": lng,
                    "direction": int(float(p[1])) if p[1] else 0,
                    "speed":     int(float(p[0])) if p[0] else 0,
                    "decimalOdometer":        None,
                    "eventType_Id":           None,
                    "eventType_Description":  None,
                    "eventType_MapMarker2":   None,
                })
            except (ValueError, IndexError):
                continue

        print(f"✅ TrackSolid events: {len(events)} valid waypoints from {len(points_raw)} total")
        return {"success": True, "count": len(events), "events": events}

    # ── MZone ─────────────────────────────────────────────────────────────────
    from app.services.mzone_service import mzone_service

    events_data = mzone_service.get_trip_events(trip_id)
    if not events_data:
        return {"success": False, "error": "Failed to fetch trip events from MZone", "events": []}

    events = events_data.get("value", [])
    print(f"✅ MZone trip events: {len(events)} waypoints")
    return {"success": True, "count": len(events), "events": events}

