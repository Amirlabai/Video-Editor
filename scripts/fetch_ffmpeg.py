#!/usr/bin/env python3
"""
Download and extract Windows FFmpeg binaries for bundling in ffmpegMagic.

Uses BtbN FFmpeg-Builds (GPL shared) — required for libx264 used by this app.
See vendor/ffmpeg/NOTICE.txt and https://www.ffmpeg.org/legal.html
"""

import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "vendor" / "ffmpeg" / "win64"
DOWNLOAD_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl-shared.zip"
)
USER_AGENT = "ffmpegMagic-fetch-ffmpeg/1.0"


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def fetch(force: bool = False) -> Path:
    DEST.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = DEST / "ffmpeg.exe"
    if ffmpeg_exe.is_file() and not force:
        print(f"FFmpeg already present: {ffmpeg_exe}")
        return DEST

    print(f"Downloading {DOWNLOAD_URL}")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "ffmpeg.zip"
        _download(DOWNLOAD_URL, zip_path)

        extract_root = Path(tmp) / "extract"
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)

        bin_dirs = list(extract_root.rglob("bin"))
        if not bin_dirs:
            raise RuntimeError("Could not find bin/ in FFmpeg archive")
        bin_dir = bin_dirs[0]

        if DEST.exists():
            shutil.rmtree(DEST)
        DEST.mkdir(parents=True)

        for item in bin_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, DEST / item.name)

        for name in ("LICENSE", "LICENSE.txt", "COPYING"):
            for lic in extract_root.rglob(name):
                shutil.copy2(lic, DEST / "LICENSE.txt")
                break

        (DEST / "SOURCE.txt").write_text(
            f"URL: {DOWNLOAD_URL}\n"
            "Provider: BtbN/FFmpeg-Builds (https://github.com/BtbN/FFmpeg-Builds)\n"
            "Project: FFmpeg (https://ffmpeg.org)\n",
            encoding="utf-8",
        )

    if not (DEST / "ffmpeg.exe").is_file() or not (DEST / "ffprobe.exe").is_file():
        raise RuntimeError("ffmpeg.exe or ffprobe.exe missing after extract")

    print(f"FFmpeg installed to {DEST}")
    return DEST


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Windows FFmpeg for bundling")
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    args = parser.parse_args()
    try:
        fetch(force=args.force)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
