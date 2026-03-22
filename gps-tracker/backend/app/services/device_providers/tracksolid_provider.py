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
- Location: getMonitorInfo endpoint returns current lat/lng, address, battery.
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
_MONITOR_URL = f"{_BASE_URL}/v3/new/newMonitor/getMonitorInfo"


@dataclass
class TrackSolidLocationInfo:
    """Location data returned by the TrackSolid getMonitorInfo endpoint."""
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


# ── TrackSolid location helper (used by location poller) ───────────────────

async def fetch_tracksolid_location(imei: str) -> "TrackSolidLocationInfo | None":
    """
    Fetch the current location for a TrackSolid IMEI via getMonitorInfo.

    Parses lat/lng from the nested ``latlng`` → ``source_latlng`` field and
    also extracts the human-readable address and battery level when present.
    Returns None if the location cannot be determined.
    """
    try:
        token = await _token_manager.get_token()
    except Exception as exc:
        logger.error("TrackSolid location: token fetch failed: %s", exc)
        return None

    _, _, user_id, _ = _creds()
    payload = {
        "imei": imei.strip(),
        "userId": user_id,
        "isAllFlag": 1,
    }
    headers = {"Authorization": token, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(_MONITOR_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.error("TrackSolid getMonitorInfo failed for IMEI %s: %s", imei, exc)
        return None

    # The response wraps an info list; handle multiple shapes
    raw = data.get("data") or {}
    if isinstance(raw, list):
        info_list = raw
    elif isinstance(raw, dict):
        info_list = (
            raw.get("infoList")
            or raw.get("list")
            or raw.get("info")
            or []
        )
    else:
        info_list = []

    if not info_list:
        logger.warning("TrackSolid getMonitorInfo: empty info list for IMEI %s. Response keys: %s", imei, list(data.keys()))
        return None

    # Build a dict keyed by the "key" field for easy access
    info_map: dict = {}
    for item in info_list:
        if isinstance(item, dict) and "key" in item:
            info_map[item["key"]] = item.get("value")

    # ── Parse lat/lng ──
    lat: float | None = None
    lng: float | None = None
    latlng_data = info_map.get("latlng")
    if isinstance(latlng_data, list):
        for entry in latlng_data:
            if isinstance(entry, dict) and entry.get("key") == "source_latlng":
                coords = str(entry.get("value", "")).strip()
                if "," in coords:
                    try:
                        parts = coords.split(",", 1)
                        lat = float(parts[0])
                        lng = float(parts[1])
                    except (ValueError, IndexError):
                        pass
    elif isinstance(latlng_data, str) and "," in latlng_data:
        try:
            parts = latlng_data.split(",", 1)
            lat = float(parts[0])
            lng = float(parts[1])
        except (ValueError, IndexError):
            pass

    if lat is None or lng is None:
        logger.warning("TrackSolid: could not parse latlng for IMEI %s, info_map keys: %s", imei, list(info_map.keys()))
        return None

    # ── Parse address ──
    raw_address = info_map.get("address")
    address: str | None = raw_address if isinstance(raw_address, str) else None

    # ── Parse battery ──
    battery_level: int | None = None
    elec = info_map.get("elecQuantity") or info_map.get("electricity") or ""
    if elec:
        try:
            battery_level = int(float(str(elec).rstrip("%")))
        except (ValueError, TypeError):
            pass

    logger.info(
        "✅ TrackSolid location for IMEI %s: lat=%.6f lng=%.6f battery=%s",
        imei, lat, lng, battery_level,
    )
    return TrackSolidLocationInfo(
        latitude=lat,
        longitude=lng,
        address=address,
        battery_level=battery_level,
    )
