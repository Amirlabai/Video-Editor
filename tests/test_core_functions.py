"""Tests for path helpers."""

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from utils import core_functions as cf  # noqa: E402


def test_resource_path_web_index():
    p = cf.resource_path("web/index.html")
    assert Path(p).exists()


def test_get_data_path_creates_user_data():
    p = cf.get_data_path("test_config.json")
    assert "user_data" in p.replace("\\", "/") or "ffmpegMagic" in p


def test_asset_file_uri_format():
    uri = cf.asset_file_uri("web/index.html")
    assert uri.startswith("file:///")


def test_materialize_splash_url(tmp_path, monkeypatch):
    monkeypatch.setattr(cf, "get_data_path", lambda rel="": str(tmp_path / rel))
    uri = cf.materialize_splash_url()
    assert uri.startswith("file:")
    cached = tmp_path / "ffmpegMagic_splash_materialized.html"
    assert cached.exists()
    text = cached.read_text(encoding="utf-8")
    assert "{{INDEX_URI}}" not in text
    assert "file:" in text
