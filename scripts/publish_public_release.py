#!/usr/bin/env python3
"""
Build latest.json for the in-app update checker and validate installer assets.

Installer .exe files are uploaded to GitHub Releases on this repo (public).
See .github/workflows/release-installer.yml
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

APP_NAME = "ffmpegMagic"
DEFAULT_REPO = os.environ.get("GITHUB_REPOSITORY", "Amirlabai/Video-Editor")


def repo_slug() -> str:
    return os.environ.get("FFMPEGMAGIC_RELEASES_REPO", DEFAULT_REPO)


def build_manifest(version: str, installer_url: str, release_page: str, notes: str) -> dict:
    return {
        "version": version,
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "installer_url": installer_url,
        "release_page": release_page,
        "notes": notes,
    }


def manifest_urls(version: str, installer_name: str, owner_repo: str) -> tuple[str, str]:
    owner, name = owner_repo.split("/", 1)
    tag = f"v{version}"
    installer_url = f"https://github.com/{owner}/{name}/releases/download/{tag}/{installer_name}"
    release_page = f"https://github.com/{owner}/{name}/releases/tag/{tag}"
    return installer_url, release_page


def validate_installer_path(version: str, path: Path) -> None:
    expected = f"{APP_NAME}_Setup_{version}.exe"
    if path.name != expected:
        raise ValueError(f"Installer must be named {expected}, got {path.name}")
    if not path.is_file():
        raise FileNotFoundError(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build latest.json for ffmpegMagic updates")
    parser.add_argument("--version", required=True)
    parser.add_argument("--installer", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--write-manifest", metavar="PATH", help="Write latest.json to this path")
    parser.add_argument("--repo", default=None, help="owner/repo (default: GITHUB_REPOSITORY or Amirlabai/Video-Editor)")
    args = parser.parse_args()

    installer = Path(args.installer)
    validate_installer_path(args.version, installer)

    owner_repo = args.repo or repo_slug()
    installer_url, release_page = manifest_urls(args.version, installer.name, owner_repo)
    manifest = build_manifest(args.version, installer_url, release_page, args.notes)

    print(json.dumps(manifest, indent=2))

    if args.write_manifest:
        out = Path(args.write_manifest)
        out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
