"""
Notify-only update checker: fetch latest.json, semver compare, throttle/snooze.
"""

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/Amirlabai/Video-Editor/main/latest.json"
)
USER_AGENT = "ffmpegMagic-UpdateChecker"
STARTUP_CHECK_INTERVAL = timedelta(hours=24)
SNOOZE_INTERVAL = timedelta(days=1)


def _parse_version(version: str) -> tuple:
    v = (version or "").strip().lstrip("vV")
    parts = re.findall(r"\d+", v)
    while len(parts) < 3:
        parts.append("0")
    return tuple(int(p) for p in parts[:3])


def _is_newer(current: str, latest: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _get_update_config(user_config: Dict[str, Any]) -> Dict[str, Any]:
    updates = user_config.setdefault("updates", {})
    updates.setdefault("update_check_enabled", True)
    updates.setdefault("update_last_check_at", "")
    updates.setdefault("update_snooze_until", "")
    updates.setdefault("update_skip_version", "")
    return updates


def fetch_manifest(url: str = DEFAULT_MANIFEST_URL, timeout: int = 15) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_for_update(
    current_version: str,
    user_config: Dict[str, Any],
    force: bool = False,
    manifest_url: str = DEFAULT_MANIFEST_URL,
) -> Dict[str, Any]:
    updates = _get_update_config(user_config)

    if not updates.get("update_check_enabled", True):
        return {"reason": "disabled", "update_available": False, "available": False}

    now = datetime.now(timezone.utc)
    skip_version = updates.get("update_skip_version", "")
    snooze_until = _parse_iso(updates.get("update_snooze_until", ""))
    if snooze_until and now < snooze_until:
        return {"reason": "snooze", "update_available": False, "available": False}

    last_check = _parse_iso(updates.get("update_last_check_at", ""))
    if not force and last_check and (now - last_check) < STARTUP_CHECK_INTERVAL:
        return {"reason": "recently_checked", "update_available": False, "available": False}

    try:
        manifest = fetch_manifest(manifest_url)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        logger.warning(f"Update check failed: {e}")
        return {"reason": "offline", "update_available": False, "available": False, "message": str(e)}

    latest_version = (manifest.get("version") or "").strip()
    if not latest_version:
        return {"reason": "error", "update_available": False, "available": False, "message": "Invalid manifest"}

    if skip_version and skip_version == latest_version:
        return {"reason": "skipped", "update_available": False, "available": False, "latest_version": latest_version}

    if not _is_newer(current_version, latest_version):
        return {"reason": "up_to_date", "update_available": False, "available": False, "current_version": current_version}

    return {
        "reason": "available",
        "update_available": True,
        "available": True,
        "current_version": current_version,
        "latest_version": latest_version,
        "installer_url": manifest.get("installer_url", ""),
        "release_page": manifest.get("release_page", ""),
        "notes": manifest.get("notes", ""),
        "published_at": manifest.get("published_at", ""),
    }


def apply_snooze(user_config: Dict[str, Any], action: str, latest_version: str) -> None:
    updates = _get_update_config(user_config)
    now = datetime.now(timezone.utc)
    if action == "skip":
        updates["update_skip_version"] = latest_version
    else:
        until = now + SNOOZE_INTERVAL
        updates["update_snooze_until"] = until.strftime("%Y-%m-%dT%H:%M:%SZ")
