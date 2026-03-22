"""
TrackSolid device provider.

Implements the Strategy interface for tags registered on the TrackSolid
(eu.tracksolidpro.com) platform.

Key concerns:
- TrackSolid rate-limits token requests. The token is valid for 1 hour.
  TrackSolidTokenManager (Singleton) caches it per worker process and only
  fetches a fresh one when the current token is within 60 seconds of expiry.
- Credentials are stored server-side only — never sent to the mobile client.
- Validation: log in → list all equipment → check if the IMEI appears.
- Location: uses the TrackSolid Open API (eu-open.tracksolidpro.com) which
  returns all device lat/lng in a single bulk call for efficiency.
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass

import httpx

from .base_provider import DeviceTagProvider, TagValidationResult

logger = logging.getLogger(__name__)

# ── TrackSolid API constants ────────────────────────────────────────────────
_BASE_URL = "https://eu.tracksolidpro.com"
_LOGIN_URL = f"{_BASE_URL}/v3/new/homepage/login"
_EQUIPMENT_URL = f"{_BASE_URL}/v3/new/newEquipment/queryEquipmentList"
_TRACK_HISTORY_URL = f"{_BASE_URL}/v3/new/newTrackInfo/getPointList"

# Open API — used for location polling (MD5-signed, separate credentials)
_OPEN_API_URL = "https://eu-open.tracksolidpro.com/route/rest"
_OPEN_TOKEN_TTL_SECONDS = 7200    # expires_in requested from the API
_OPEN_TOKEN_REFRESH_BUFFER = 120  # Refresh 2 min before expiry


@dataclass
class TrackSolidLocationInfo:
    """Location data returned by the TrackSolid Open API."""
    latitude: float
    longitude: float
    address: str | None = None
    battery_level: int | None = None  # 0-100 parsed from elecQuantity

# Credentials are read lazily from env vars when first needed.
# Reading them at module level would crash startup if they aren't set yet.
def _creds() -> tuple[str, str, int, str]:
    """Return (account, password, user_id, org_id) from environment."""
    return (
        os.environ["TRACKSOLID_ACCOUNT"],
        os.environ["TRACKSOLID_PASSWORD"],
        int(os.environ["TRACKSOLID_USER_ID"]),
        os.environ["TRACKSOLID_ORG_ID"],
    )

_TOKEN_TTL_SECONDS = 3600       # TrackSolid tokens last 1 hour
_TOKEN_REFRESH_BUFFER = 60      # Refresh 60 s before expiry to be safe


# ── Singleton token manager ──────────────────────────────────────────────────
class TrackSolidTokenManager:
    """
    Singleton that holds one TrackSolid JWT per worker process.

    asyncio.Lock ensures only one coroutine fetches a new token at a time,
    preventing duplicate login calls when multiple requests arrive simultaneously
    while the token is being refreshed.
    """

    _instance: "TrackSolidTokenManager | None" = None
    # Declared here so type checkers know the shape; values set in __new__
    _token: "str | None"
    _expires_at: float
    _lock: asyncio.Lock

    def __new__(cls) -> "TrackSolidTokenManager":
        if cls._instance is None:
            inst = object.__new__(cls)
            inst._token = None
            inst._expires_at = 0.0
            inst._lock = asyncio.Lock()
            cls._instance = inst
        return cls._instance

    async def get_token(self) -> str:
        """Return a valid token, fetching a new one only when necessary."""
        async with self._lock:
            now = time.time()
            if self._token and now < self._expires_at - _TOKEN_REFRESH_BUFFER:
                remaining = int(self._expires_at - now)
                logger.info(
                    "♻️  TrackSolid: reusing cached token (expires in %ds)", remaining
                )
                return self._token

            logger.info("🔄 TrackSolid: fetching new token (old token expired or absent)")
            self._token = await self._fetch_token()
            self._expires_at = time.time() + _TOKEN_TTL_SECONDS
            logger.info("✅ TrackSolid: new token obtained, valid for ~1 hour")
            return self._token

    async def _fetch_token(self) -> str:
        account, password, _, _ = _creds()
        password_md5 = hashlib.md5(password.encode()).hexdigest().lower()
        payload = {
            "account": account,
            "password": password_md5,
            "language": "en",
            "validCode": "",
            "nodeId": "",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(_LOGIN_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        # TrackSolid V3 API stores the JWT in one of several possible paths.
        # Try the most common ones in order.
        token = (
            (data.get("data") or {}).get("authorization")
            or (data.get("data") or {}).get("token")
            or data.get("authorization")
            or data.get("token")
            or data.get("accessToken")
        )
        if not token:
            raise RuntimeError(
                f"TrackSolid login succeeded (HTTP {response.status_code}) "
                f"but no token found in response: {list(data.keys())}"
            )
        return token


# Module-level singleton instance
_token_manager = TrackSolidTokenManager()


# ── TrackSolid tag provider (Strategy) ─────────────────────────────────────
class TrackSolidTagProvider(DeviceTagProvider):
    """
    Validates a BLE tag IMEI against the Beacontelematics TrackSolid account.

    Flow:
      1. Obtain (or reuse) a valid JWT via TrackSolidTokenManager.
      2. POST to the equipment list endpoint.
      3. If the IMEI is present → valid; otherwise → "Tag not found on TrackSolid".
    """

    @property
    def provider_name(self) -> str:
        return "TrackSolid"

    @property
    def tag_type(self) -> str:
        return "tracksolid"

    async def validate_tag(self, imei: str) -> TagValidationResult:
        try:
            token = await _token_manager.get_token()
        except Exception as exc:
            logger.error("TrackSolid token fetch failed: %s", exc)
            return TagValidationResult(
                is_valid=False,
                message="Could not connect to TrackSolid. Please try again later.",
            )

        _, _, user_id, org_id = _creds()
        payload = {
            "imei": imei.strip(),  # filter to this IMEI avoids pagination issues
            "startRow": "0",
            "userType": 8,
            "userId": user_id,
            "orgId": org_id,
            "siftType": "",
            "sortType": "",
            "sortRule": "",
            "isNewMcType": "0",
            "videoEntry": "",
            "type": "NORMAL",
            "searchStatus": "ALL",
        }
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    _EQUIPMENT_URL, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("TrackSolid equipment list HTTP error: %s", exc)
            return TagValidationResult(
                is_valid=False,
                message="TrackSolid API error. Please try again later.",
            )
        except Exception as exc:
            logger.error("TrackSolid equipment list error: %s", exc)
            return TagValidationResult(
                is_valid=False,
                message="Could not reach TrackSolid. Check your connection.",
            )

        # Parse the device list — handle both wrapped and flat response shapes
        devices: list = []
        result_data = data.get("data") or data.get("result") or {}
        if isinstance(result_data, list):
            devices = result_data
        elif isinstance(result_data, dict):
            devices = (
                result_data.get("list")
                or result_data.get("data")
                or result_data.get("records")
                or []
            )

        imei_strip = imei.strip()
        logger.debug("TrackSolid returned %d device(s) for IMEI query '%s'", len(devices), imei_strip)
        found_device = None
        for device in devices:
            if str(device.get("imei", "")).strip() == imei_strip:
                found_device = device
                break

        if found_device is not None:
            # Parse elecQuantity "98.30%" → int 98
            battery_level: int | None = None
            elec = found_device.get("elecQuantity", "") or ""
            if elec:
                try:
                    battery_level = int(float(str(elec).rstrip("%")))
                except (ValueError, TypeError):
                    pass

            return TagValidationResult(
                is_valid=True,
                message="Tag verified on TrackSolid.",
                battery_level=battery_level,
            )
        return TagValidationResult(
            is_valid=False,
            message="Tag not supported — IMEI not found on TrackSolid account.",
        )


# ── TrackSolid Open API: credentials, signing, token ───────────────────────

def _creds_open() -> tuple[str, str, str]:
    """Return (account, app_key, app_secret) for the Open API from env vars."""
    return (
        os.environ["TRACKSOLID_ACCOUNT"],
        os.environ["TRACKSOLID_APP_KEY"],
        os.environ["TRACKSOLID_APP_SECRET"],
    )


def _open_api_signature(params: dict, secret: str) -> str:
    """MD5 sign: secret + sorted(key+value pairs) + secret → uppercase hex."""
    sign_str = secret
    for key in sorted(params.keys()):
        sign_str += key + str(params[key])
    sign_str += secret
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()


class TrackSolidOpenTokenManager:
    """Singleton that caches the Open API access token (valid ~2 hours)."""

    _instance: "TrackSolidOpenTokenManager | None" = None
    _token: "str | None"
    _expires_at: float
    _lock: asyncio.Lock

    def __new__(cls) -> "TrackSolidOpenTokenManager":
        if cls._instance is None:
            inst = object.__new__(cls)
            inst._token = None
            inst._expires_at = 0.0
            inst._lock = asyncio.Lock()
            cls._instance = inst
        return cls._instance

    async def get_token(self) -> str:
        async with self._lock:
            now = time.time()
            if self._token and now < self._expires_at - _OPEN_TOKEN_REFRESH_BUFFER:
                logger.info("♻️  TrackSolid Open API: reusing cached token")
                return self._token

            logger.info("🔄 TrackSolid Open API: fetching new access token")
            self._token = await self._fetch_token()
            self._expires_at = time.time() + _OPEN_TOKEN_TTL_SECONDS
            logger.info("✅ TrackSolid Open API: token obtained, valid for ~2 hours")
            return self._token

    async def _fetch_token(self) -> str:
        account, app_key, app_secret = _creds_open()
        password = os.environ["TRACKSOLID_PASSWORD"]
        pwd_md5 = hashlib.md5(password.encode("utf-8")).hexdigest().lower()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

        params: dict = {
            "app_key": app_key,
            "expires_in": "7200",
            "format": "json",
            "method": "jimi.oauth.token.get",
            "sign_method": "md5",
            "timestamp": timestamp,
            "user_id": account,       # open API uses account name as user_id
            "user_pwd_md5": pwd_md5,
            "v": "1.0",
        }
        params["sign"] = _open_api_signature(params, app_secret)

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(_OPEN_API_URL, data=params)
            response.raise_for_status()
            data = response.json()

        if data.get("code") != 0:
            raise RuntimeError(
                f"TrackSolid Open API token error: {data.get('message')} (code={data.get('code')})"
            )
        token = (data.get("result") or {}).get("accessToken")
        if not token:
            raise RuntimeError(
                f"TrackSolid Open API: no accessToken in response: {list(data.keys())}"
            )
        return token


_open_token_manager = TrackSolidOpenTokenManager()


# ── Location helpers (used by location poller) ──────────────────────────────

async def fetch_all_tracksolid_locations() -> "dict[str, TrackSolidLocationInfo]":
    """
    Fetch current locations for ALL TrackSolid devices on the account in one
    API call (jimi.user.device.location.list).

    Returns a dict keyed by IMEI string. Entries where lat==0.0 and lng==0.0
    indicate the device has no GPS fix and should be skipped by the caller.
    """
    try:
        token = await _open_token_manager.get_token()
    except Exception as exc:
        logger.error("TrackSolid Open API: token fetch failed: %s", exc)
        return {}

    account, app_key, app_secret = _creds_open()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    params: dict = {
        "access_token": token,
        "app_key": app_key,
        "format": "json",
        "method": "jimi.user.device.location.list",
        "sign_method": "md5",
        "target": account,
        "timestamp": timestamp,
        "v": "1.0",
    }
    params["sign"] = _open_api_signature(params, app_secret)

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(_OPEN_API_URL, data=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.error("TrackSolid Open API: device location list failed: %s", exc)
        return {}

    if data.get("code") != 0:
        logger.error(
            "TrackSolid Open API location list error: %s (code=%s)",
            data.get("message"), data.get("code"),
        )
        return {}

    devices: list = data.get("result") or []
    result: dict[str, TrackSolidLocationInfo] = {}
    for device in devices:
        imei = str(device.get("imei", "")).strip()
        if not imei:
            continue
        try:
            lat = float(device.get("lat") or 0)
            lng = float(device.get("lng") or 0)
        except (ValueError, TypeError):
            lat, lng = 0.0, 0.0
        result[imei] = TrackSolidLocationInfo(
            latitude=lat,
            longitude=lng,
            address=None,       # location list does not return addresses
            battery_level=None, # battery comes from equipment list only
        )

    logger.info("📡 TrackSolid Open API: fetched %d device locations", len(result))
    return result


async def fetch_tracksolid_location(imei: str) -> "TrackSolidLocationInfo | None":
    """
    Fetch the current location for a single TrackSolid IMEI.

    Calls fetch_all_tracksolid_locations() (bulk open API) and filters by IMEI.
    Returns None when the IMEI is not found or has no GPS fix (lat=lng=0).
    """
    all_locs = await fetch_all_tracksolid_locations()
    loc = all_locs.get(imei.strip())
    if not loc:
        logger.warning("TrackSolid: IMEI %s not found in device location response", imei)
        return None
    if loc.latitude == 0.0 and loc.longitude == 0.0:
        logger.warning("TrackSolid: IMEI %s has no GPS fix (lat=0, lng=0)", imei)
        return None
    return loc


async def fetch_tracksolid_journey_points(
    imei: str,
    start_time: str,
    end_time: str,
) -> "dict | None":
    """
    Fetch GPS track points for a TrackSolid device over a date range.

    Uses the V3 Bearer token (JWT from login endpoint — same token used for
    equipment validation, NOT the Open API MD5 token).

    start_time / end_time format: "YYYY-MM-DD HH:MM:SS"

    Returns the raw API ``data`` dict on success, which contains:
      - ``gpsPointStrList``: pipe-delimited point strings
      - ``startAddress``, ``endAddress``
      - ``totalMileage``, ``showUnit``, ``avgSpeed``, ``speedUnit``
      - ``startDate``, ``endDate`` ("YYYY-MM-DD HH:MM:SS")
      - ``deviceName``, ``imei``
    Returns None on error.
    """
    try:
        token = await _token_manager.get_token()
    except Exception as exc:
        logger.error("TrackSolid: token fetch failed for journey points: %s", exc)
        return None

    payload = {
        "startTime": start_time,
        "endTime": end_time,
        "imei": imei,
        "confidenceLevel": "",
        "selectMap": "googleMap",
        "selectType": "all",
    }
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                _TRACK_HISTORY_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.error("TrackSolid: getPointList failed for IMEI %s: %s", imei, exc)
        return None

    if not data.get("ok"):
        logger.error(
            "TrackSolid: getPointList ok=false for IMEI %s: code=%s msg=%s",
            imei, data.get("code"), data.get("msg"),
        )
        return None

    track_data = data.get("data")
    logger.info(
        "📍 TrackSolid journey: IMEI %s — %d points, %s %s",
        imei,
        len((track_data or {}).get("gpsPointStrList") or []),
        (track_data or {}).get("totalMileage", "0"),
        (track_data or {}).get("showUnit", ""),
    )
    return track_data
