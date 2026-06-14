# ffmpegMagic

A Python-based desktop app for FFmpeg video scaling and joining. The GUI uses **PyWebView + WebView2** on Windows; agents use a headless CLI.

## Features

- Scale/compress videos (CPU or GPU NVENC)
- Batch queue with progress metrics
- Join multiple videos in a folder
- Persistent settings in user config
- Notify-only update checker
- Agent drop-and-go workflow via `.incoming/` and `cli.py`

## Prerequisites

- Python 3.11+ (development only)
- [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (usually preinstalled on Windows 11)

The Windows installer **bundles FFmpeg** (fetched at build time from [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds)). See [vendor/ffmpeg/NOTICE.txt](vendor/ffmpeg/NOTICE.txt) and https://ffmpeg.org/legal.html for license and attribution.

For development without building an installer, either:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_ffmpeg.py
```

or install FFmpeg on PATH: https://ffmpeg.org/download.html

## Setup

```powershell
git clone https://github.com/YourUsername/Video-Editor.git
cd Video-Editor
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run (GUI)

```powershell
.\.venv\Scripts\python.exe src\web_app.py
```

Dev shortcut (skip splash):

```powershell
$env:FFMPEGMAGIC_SKIP_SPLASH = "1"
.\.venv\Scripts\python.exe src\web_app.py
```

## Run (CLI / agents)

```powershell
.\.venv\Scripts\python.exe src\cli.py list
.\.venv\Scripts\python.exe src\cli.py compress
.\.venv\Scripts\python.exe src\cli.py join
```

See [agent_instructions.md](agent_instructions.md).

## Build (Windows)

```powershell
.\.venv\Scripts\python.exe prod\gen_exe.py
```

Set `INNO_SETUP_PATH` if Inno Setup is not in a default location:

```powershell
$env:INNO_SETUP_PATH = "C:\Users\amirl\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
.\.venv\Scripts\python.exe prod\gen_exe.py
```

The build downloads FFmpeg automatically if `vendor/ffmpeg/win64/ffmpeg.exe` is missing.

Output: `prod/installers/ffmpegMagic_Setup_{version}.exe`. PyInstaller intermediates go to `installer_files_{version}/`.

## Release (this public repo)

No separate releases repo. Installers are built in CI and attached to GitHub Release tags on [Amirlabai/Video-Editor](https://github.com/Amirlabai/Video-Editor).

1. Push features to `main` — semantic-release creates tag `vX.Y.Z` and a GitHub Release.
2. **Build and Release Installer** runs after Semantic Release completes (GitHub does not fire `release: published` for releases created by `GITHUB_TOKEN`).
3. Windows job: `prod/gen_exe.py` → uploads `ffmpegMagic_Setup_X.Y.Z.exe` to that tag → commits `latest.json`.

Backfill an existing tag: Actions → **Build and Release Installer** → Run workflow → version `X.Y.Z`.

Update manifest URL: `https://raw.githubusercontent.com/Amirlabai/Video-Editor/main/latest.json`

## Development

- Version: `src/_version.py`
- Semantic release on push to `main`
- Tests: `.\.venv\Scripts\python.exe -m pytest tests/ -v`
- Architecture notes: `architecture/`
- Accessibility draft: `docs/accessibility.md`

## License

MIT License
