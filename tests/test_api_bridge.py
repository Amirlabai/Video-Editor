"""Tests for VideoEditorApi bridge helpers."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from bridge.api_bridge import VideoEditorApi  # noqa: E402


@pytest.fixture
def api():
    return VideoEditorApi()


def test_ok_envelope(api):
    r = api._ok({"foo": "bar"})
    assert r["status"] == "success"
    assert r["foo"] == "bar"


def test_err_envelope(api):
    r = api._err("boom")
    assert r["status"] == "error"
    assert r["message"] == "boom"


def test_settings_get_path(api):
    r = api.settings_get_path()
    assert r["status"] == "success"
    assert "file" in r
    assert "directory" in r


def test_compress_get_options(api):
    r = api.compress_get_options()
    assert r["status"] == "success"
    assert "fps_options" in r
    assert "defaults" in r


@patch("bridge.api_bridge.VideoEditorApi._check_ffmpeg", return_value=True)
def test_prepare_startup(mock_ff, api):
    r = api.prepare_startup()
    assert r["status"] == "success"


def test_check_for_updates_offline(api):
    with patch("utils.update_check.check_for_update", return_value={"reason": "offline", "update_available": False, "available": False}):
        r = api.check_for_updates(force=True)
    assert r["status"] == "success"
    assert r.get("reason") == "offline"
