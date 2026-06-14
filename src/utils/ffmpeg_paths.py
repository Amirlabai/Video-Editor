"""
Resolve bundled or system FFmpeg / ffprobe executables.
"""

import os
import sys
from pathlib import Path
from typing import Optional

FFMPEG_PROJECT_URL = "https://ffmpeg.org"
FFMPEG_LEGAL_URL = "https://www.ffmpeg.org/legal.html"
FFMPEG_SOURCE_URL = "https://github.com/BtbN/FFmpeg-Builds"

_NOTICE_FILE = "NOTICE.txt"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _vendor_win64_dir() -> Path:
    try:
        from utils.core_functions import resource_path
        return Path(resource_path("vendor/ffmpeg/win64"))
    except ImportError:
        return _repo_root() / "vendor" / "ffmpeg" / "win64"


def get_ffmpeg_exe() -> str:
    bundled = _vendor_win64_dir() / "ffmpeg.exe"
    if bundled.is_file():
        return str(bundled.resolve())
    return "ffmpeg"


def get_ffprobe_exe() -> str:
    bundled = _vendor_win64_dir() / "ffprobe.exe"
    if bundled.is_file():
        return str(bundled.resolve())
    return "ffprobe"


def is_bundled() -> bool:
    return (_vendor_win64_dir() / "ffmpeg.exe").is_file()


def ffmpeg_bin_dir() -> Optional[str]:
    """Directory containing bundled ffmpeg (for PATH augmentation if needed)."""
    d = _vendor_win64_dir()
    if (d / "ffmpeg.exe").is_file():
        return str(d.resolve())
    return None


def subprocess_env() -> Optional[dict]:
    """Optional env with bundled bin on PATH (helps shared builds find DLLs)."""
    bin_dir = ffmpeg_bin_dir()
    if not bin_dir:
        return None
    env = os.environ.copy()
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    return env


def check_ffmpeg_available() -> bool:
    import subprocess
    try:
        subprocess.run(
            [get_ffmpeg_exe(), "-version"],
            capture_output=True,
            check=True,
            timeout=15,
            env=subprocess_env(),
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def read_notice_text() -> str:
    for base in (_vendor_win64_dir().parent, _repo_root() / "vendor" / "ffmpeg"):
        notice = base / _NOTICE_FILE
        if notice.is_file():
            return notice.read_text(encoding="utf-8")
    return (
        "This software uses command-line tools from the FFmpeg project "
        "(https://ffmpeg.org), licensed under the GNU LGPL version 2.1 or later; "
        "some builds may include GPL-licensed components. "
        "FFmpeg is a trademark of Fabrice Bellard. "
        f"See {FFMPEG_LEGAL_URL}"
    )


def get_ffmpeg_info() -> dict:
    exe = get_ffmpeg_exe()
    bundled = is_bundled()
    version_line = ""
    if check_ffmpeg_available():
        import subprocess
        try:
            r = subprocess.run(
                [exe, "-version"],
                capture_output=True,
                text=True,
                timeout=15,
                env=subprocess_env(),
            )
            version_line = (r.stdout or "").splitlines()[0] if r.stdout else ""
        except Exception:
            pass
    source_meta = _vendor_win64_dir() / "SOURCE.txt"
    source_url = source_meta.read_text(encoding="utf-8").strip() if source_meta.is_file() else FFMPEG_SOURCE_URL
    return {
        "bundled": bundled,
        "executable": exe,
        "version_line": version_line,
        "project_url": FFMPEG_PROJECT_URL,
        "legal_url": FFMPEG_LEGAL_URL,
        "source_url": source_url,
        "notice": read_notice_text(),
    }
