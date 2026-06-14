"""Tests for ProgressReporter with VideoProcessor (no Tk)."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from models.progress_reporter import NullProgressReporter, PrintProgressReporter  # noqa: E402
from models.VideoProcessor import VideoProcessor  # noqa: E402


def test_null_reporter_does_not_raise():
    rep = NullProgressReporter()
    rep.on_progress({"percent": 50})
    rep.on_log("test\n")
    rep.on_file_status(0, "Pending")


def test_print_reporter_logs():
    rep = PrintProgressReporter()
    rep.on_log("hello\n")


def test_video_processor_has_no_tk_import():
    import models.VideoProcessor as vp
    source = Path(vp.__file__).read_text(encoding="utf-8")
    assert "tkinter" not in source
    assert "messagebox" not in source


def test_format_file_size():
    assert "KB" in VideoProcessor.format_file_size(2048)
