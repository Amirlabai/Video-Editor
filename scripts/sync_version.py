#!/usr/bin/env python3
"""Sync src/_version.py from pyproject.toml project.version."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
VERSION_PY = ROOT / "src" / "_version.py"


def read_pyproject_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not find project.version in {PYPROJECT}")
    return match.group(1)


def main() -> int:
    version = read_pyproject_version()
    VERSION_PY.write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    print(f"Synced {VERSION_PY.name} -> {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
