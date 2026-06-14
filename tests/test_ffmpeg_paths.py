"""Tests for bundled FFmpeg path resolution."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from utils import ffmpeg_paths  # noqa: E402


def test_get_ffmpeg_exe_fallback():
    with patch.object(ffmpeg_paths, "_vendor_win64_dir") as mock_dir:
        mock_dir.return_value = Path("/nonexistent/vendor")
        assert ffmpeg_paths.get_ffmpeg_exe() == "ffmpeg"


def test_read_notice_text_contains_ffmpeg():
    text = ffmpeg_paths.read_notice_text()
    assert "FFmpeg" in text
    assert "ffmpeg.org" in text


def test_get_ffmpeg_info_keys():
    info = ffmpeg_paths.get_ffmpeg_info()
    assert "bundled" in info
    assert "notice" in info
    assert "legal_url" in info
    assert "https://ffmpeg.org" in info["project_url"]
