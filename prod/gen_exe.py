"""
PyInstaller + Inno Setup build script for ffmpegMagic.
Run: .\.venv\Scripts\python.exe prod\gen_exe.py

Environment:
  INNO_SETUP_PATH — path to ISCC.exe (e.g. C:\\Users\\...\\Inno Setup 6\\ISCC.exe)
"""

import os
import subprocess
import sys
from pathlib import Path

PROD = Path(__file__).resolve().parent
ROOT = PROD.parent
SRC = ROOT / "src"
VERSION_FILE = SRC / "_version.py"
INNO_SCRIPT = PROD / "create_installer.iss"
INSTALLER_DIR = PROD / "installers"
APP_NAME = "ffmpegMagic"
EXE_NAME = f"{APP_NAME}.exe"

FALLBACK_ISCC_PATHS = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(os.path.expandvars(r"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe")),
]


def get_version() -> str:
    ns = {}
    exec(VERSION_FILE.read_text(encoding="utf-8"), ns)
    return ns["__version__"]


def find_iscc() -> Path:
    env = os.environ.get("INNO_SETUP_PATH", "").strip()
    if env:
        path = Path(env)
        if path.is_file():
            return path
        raise FileNotFoundError(f"INNO_SETUP_PATH does not point to a file: {env}")
    for candidate in FALLBACK_ISCC_PATHS:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "ISCC.exe not found. Install Inno Setup 6 or set INNO_SETUP_PATH to ISCC.exe."
    )


def pyinstaller_dist_dir(version: str) -> Path:
    return ROOT / f"installer_files_{version}" / APP_NAME


def ensure_ffmpeg_vendor() -> None:
    """Download FFmpeg binaries if missing (Windows installer bundle)."""
    vendor_exe = ROOT / "vendor" / "ffmpeg" / "win64" / "ffmpeg.exe"
    if vendor_exe.is_file():
        print(f"Bundled FFmpeg present: {vendor_exe}")
        return
    fetch_script = ROOT / "scripts" / "fetch_ffmpeg.py"
    if not fetch_script.is_file():
        raise FileNotFoundError(
            f"FFmpeg not found at {vendor_exe} and {fetch_script} is missing."
        )
    print("Fetching FFmpeg for bundling...")
    subprocess.run([sys.executable, str(fetch_script)], cwd=str(ROOT), check=True)


def run_pyinstaller(version: str) -> Path:
    out_dir = ROOT / f"installer_files_{version}"
    out_dir.mkdir(parents=True, exist_ok=True)
    app_bundle = pyinstaller_dist_dir(version)

    sep = ";" if sys.platform == "win32" else ":"
    add_data = [
        f"{SRC / 'web'}{sep}web",
        f"{ROOT / 'assets'}{sep}assets",
        f"{ROOT / 'vendor' / 'ffmpeg' / 'win64'}{sep}vendor/ffmpeg/win64",
        f"{ROOT / 'vendor' / 'ffmpeg' / 'NOTICE.txt'}{sep}vendor/ffmpeg",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--distpath={out_dir}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={PROD}",
        str(SRC / "web_app.py"),
    ]

    icon = ROOT / "assets" / "ffmpegMagic.ico"
    if icon.is_file():
        cmd.append(f"--icon={icon}")

    for item in add_data:
        cmd.extend(["--add-data", item])

    print("Running PyInstaller...")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    exe_path = app_bundle / EXE_NAME
    if not exe_path.is_file():
        raise FileNotFoundError(f"PyInstaller did not produce: {exe_path}")
    print(f"PyInstaller complete: {exe_path}")
    return exe_path


def run_inno(version: str) -> Path:
    iscc = find_iscc()
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)

    bundle = pyinstaller_dist_dir(version)
    if not (bundle / EXE_NAME).is_file():
        raise FileNotFoundError(f"App bundle missing before Inno compile: {bundle}")

    cmd = [
        str(iscc),
        f"/DMyAppVersion={version}",
        str(INNO_SCRIPT),
    ]
    print("Running Inno Setup...")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=str(PROD), check=True)

    installer = INSTALLER_DIR / f"{APP_NAME}_Setup_{version}.exe"
    if not installer.is_file():
        raise FileNotFoundError(f"Inno Setup did not produce: {installer}")

    for old in INSTALLER_DIR.glob(f"{APP_NAME}_Setup_*.exe"):
        if old.resolve() != installer.resolve():
            print(f"Removing old installer: {old.name}")
            old.unlink()

    print(f"Installer complete: {installer}")
    return installer


def main() -> None:
    if sys.platform != "win32":
        print("Warning: installer build is intended for Windows.", file=sys.stderr)

    version = get_version()
    ensure_ffmpeg_vendor()
    run_pyinstaller(version)
    run_inno(version)


if __name__ == "__main__":
    main()
