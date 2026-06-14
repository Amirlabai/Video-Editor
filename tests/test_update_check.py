"""Tests for update_check."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from utils import update_check  # noqa: E402


def test_parse_version_order():
    assert update_check._is_newer("1.0.0", "1.0.1")
    assert not update_check._is_newer("2.0.0", "1.9.9")


def test_up_to_date():
    cfg = {"updates": {"update_check_enabled": True}}
    with patch.object(update_check, "fetch_manifest", return_value={"version": "0.1.0"}):
        r = update_check.check_for_update("0.1.0", cfg, force=True)
    assert r["reason"] == "up_to_date"
    assert not r["update_available"]


def test_available():
    cfg = {"updates": {"update_check_enabled": True}}
    manifest = {
        "version": "9.0.0",
        "installer_url": "https://example.com/setup.exe",
        "release_page": "https://example.com/releases",
        "notes": "Test",
    }
    with patch.object(update_check, "fetch_manifest", return_value=manifest):
        r = update_check.check_for_update("0.1.0", cfg, force=True)
    assert r["reason"] == "available"
    assert r["update_available"]


def test_recently_checked_throttle():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg = {"updates": {"update_check_enabled": True, "update_last_check_at": now}}
    r = update_check.check_for_update("0.1.0", cfg, force=False)
    assert r["reason"] == "recently_checked"


def test_snooze():
    until = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg = {"updates": {"update_snooze_until": until, "update_check_enabled": True}}
    r = update_check.check_for_update("0.1.0", cfg, force=True)
    assert r["reason"] == "snooze"
