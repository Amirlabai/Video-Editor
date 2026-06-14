"""
Path helpers for dev, frozen (PyInstaller/Nuitka), and WebView2 asset loading.
"""

import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    """Repository root (parent of src/)."""
    return Path(__file__).resolve().parent.parent.parent


def _src_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_path(relative_path: str) -> str:
    """Absolute path to a bundled read-only resource."""
    rel = relative_path.replace("/", os.sep)
    if is_frozen():
        base = getattr(sys, "_MEIPASS", None)
        if base is None:
            base = os.path.join(os.path.dirname(sys.executable), "_internal")
        return os.path.join(base, rel)
    return str(_src_dir() / rel)


def get_data_path(relative_path: str = "") -> str:
    """Writable user data path (dev: user_data/, frozen: %APPDATA%/ffmpegMagic/)."""
    if is_frozen():
        base = Path(os.environ.get("APPDATA", Path.home())) / "ffmpegMagic"
    else:
        base = _repo_root() / "user_data"
    base.mkdir(parents=True, exist_ok=True)
    if relative_path:
        full = base / relative_path.replace("/", os.sep)
        full.parent.mkdir(parents=True, exist_ok=True)
        return str(full)
    return str(base)


def asset_file_uri(relative_path: str) -> str:
    """file:// URI for WebView2."""
    return Path(resource_path(relative_path)).resolve().as_uri()


def materialize_splash_url() -> str:
    """
    Read splash template, substitute asset URIs, write cache, return file URI.
    Placeholders: {{LOGO_URI}}, {{INDEX_URI}}
    """
    template_path = Path(resource_path("web/splash.html"))
    cache_path = Path(get_data_path("ffmpegMagic_splash_materialized.html"))
    index_uri = asset_file_uri("web/index.html")
    logo_uri = asset_file_uri("assets/ffmpegMagic.ico")
    style_uri = asset_file_uri("web/style.css")

    content = template_path.read_text(encoding="utf-8")
    content = content.replace("{{LOGO_URI}}", logo_uri)
    content = content.replace("{{INDEX_URI}}", index_uri)
    content = content.replace("{{STYLE_URI}}", style_uri)
    cache_path.write_text(content, encoding="utf-8")
    return cache_path.resolve().as_uri()


def get_log_path() -> str:
    if is_frozen():
        return get_data_path("ffmpegMagic_log.log")
    return str(_src_dir() / "ffmpegMagic_dev_log.log")
