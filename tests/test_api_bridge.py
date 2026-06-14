"""Tests for VideoEditorApi bridge helpers."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from bridge.api_bridge import (  # noqa: E402
    VideoEditorApi,
    _build_file_types,
    _looks_like_path,
    _normalize_dialog_dir,
)


@pytest.fixture
def api():
    return VideoEditorApi()


def test_build_file_types():
    assert _build_file_types("*.mp4;*.mkv") == ("Videos (*.mp4;*.mkv)",)
    assert _build_file_types("") == tuple()


def test_normalize_dialog_dir(tmp_path):
    assert _normalize_dialog_dir(str(tmp_path)) == str(tmp_path)
    assert _normalize_dialog_dir("/nonexistent/path/xyz") == ""


def test_looks_like_path():
    assert _looks_like_path(r"C:\Videos\clip.mp4") is True
    assert _looks_like_path("/home/clip.mp4") is True
    assert _looks_like_path("a/b") is False


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
    defaults = r["defaults"]
    assert "use_gpu" in defaults
    assert "use_all_cores" in defaults
    assert "cap_cpu_50" in defaults


def test_emit_event_calls_window_handler(api):
    api._window = MagicMock()
    api._emit_event("compress_progress", {"Progress:": "50.00%"})
    api._window.evaluate_js.assert_called_once()
    js = api._window.evaluate_js.call_args[0][0]
    assert "window.compress_progress" in js
    assert "Progress:" in js


def test_emit_event_escapes_payload(api):
    api._window = MagicMock()
    payload = {"line": 'say "hello"\nworld'}
    api._emit_event("compress_log", payload)
    js = api._window.evaluate_js.call_args[0][0]
    assert json.dumps(payload) in js


def test_pick_files(api, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    api._window = MagicMock()
    api._window.create_file_dialog.return_value = (str(video),)
    mock_webview = MagicMock()
    mock_webview.OPEN_DIALOG = 10
    with patch.dict(sys.modules, {"webview": mock_webview}):
        r = api.pick_files(str(tmp_path), "*.mp4")
    assert r["status"] == "success"
    assert r["paths"] == [str(video)]
    api._window.create_file_dialog.assert_called_once()


def test_compress_cancel_unknown_job(api):
    r = api.compress_cancel("missing-job-id")
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()


def test_compress_cancel_empty_cancels_running(api):
    api._jobs["j1"] = {"type": "compress", "state": "running"}
    with patch.object(api._processor, "cancel") as mock_cancel:
        r = api.compress_cancel("")
    assert r["status"] == "success"
    assert api._jobs["j1"]["state"] == "cancelled"
    mock_cancel.assert_called_once()


def test_join_cancel_unknown_job(api):
    r = api.join_cancel("missing-job-id")
    assert r["status"] == "error"


def test_join_cancel_empty_cancels_running(api):
    api._jobs["j1"] = {"type": "join", "state": "running"}
    with patch.object(api._joiner, "cancel") as mock_cancel:
        r = api.join_cancel("")
    assert r["status"] == "success"
    assert api._jobs["j1"]["state"] == "cancelled"
    mock_cancel.assert_called_once()


def test_run_compress_job_cancelled_emits_flag(api):
    api._window = MagicMock()
    job_id = "cancelled-job"
    api._jobs[job_id] = {"type": "compress", "state": "cancelled", "total": 0, "processed": 0}
    api._run_compress_job(job_id, [], {}, str(Path("/out")), "1920", "1080")
    js = api._window.evaluate_js.call_args[0][0]
    assert "compress_complete" in js
    assert '"cancelled":true' in js.replace(" ", "")


def test_run_join_job_cancelled(api):
    api._window = MagicMock()
    job_id = "join-cancelled"
    api._jobs[job_id] = {"type": "join", "state": "cancelled"}
    api._joiner = MagicMock()
    api._joiner.create_concat_file.return_value = "/tmp/concat.txt"
    api._joiner.join_videos.return_value = False
    with patch("bridge.api_bridge.os.path.exists", return_value=True), patch("bridge.api_bridge.os.remove"):
        api._run_join_job(job_id, "/in", "/out", ["a.mp4", "b.mp4"])
    js = api._window.evaluate_js.call_args[0][0]
    assert "join_complete" in js
    assert '"cancelled":true' in js.replace(" ", "")
    assert '"success":false' in js.replace(" ", "")


@patch("bridge.api_bridge.VideoEditorApi._check_ffmpeg", return_value=True)
def test_prepare_startup(mock_ff, api):
    r = api.prepare_startup()
    assert r["status"] == "success"


def test_check_for_updates_offline(api):
    with patch("utils.update_check.check_for_update", return_value={"reason": "offline", "update_available": False, "available": False}):
        r = api.check_for_updates(force=True)
    assert r["status"] == "success"
    assert r.get("reason") == "offline"
