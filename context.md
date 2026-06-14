# Project Context: Video-Editor (ffmpegMagic)

## Overview

A lightweight video processing tool offering scaling and joining via FFmpeg. The GUI is **PyWebView + WebView2** (HTML/CSS/JS); agents use a headless CLI.

## Architecture

| Layer | Path |
|-------|------|
| Entry (GUI) | `src/web_app.py` |
| Bridge API | `src/bridge/api_bridge.py` |
| Frontend | `src/web/` (index.html, style.css, app.js, compress.js, join.js) |
| Paths | `src/utils/core_functions.py` |
| FFmpeg | `src/utils/ffmpeg_paths.py`, `vendor/ffmpeg/` (bundled in Windows installer) |
| Updates | `src/utils/update_check.py` |
| Backends | `src/models/VideoProcessor.py`, `VideoJoiner.py`, `ConfigManager.py` |
| CLI | `src/cli.py` |
| Packaging | `prod/gen_exe.py`, `prod/create_installer.iss` |

## Technology Stack

- Python 3.11+
- PyWebView (Edge WebView2 on Windows)
- FFmpeg
- Static HTML/CSS/JS (retro dark blocky theme)

## Data paths

- Dev config/logs: `user_data/`, `src/ffmpegMagic_dev_log.log`
- Frozen config/logs: `%APPDATA%\ffmpegMagic\`
- Legacy config migration from `~/.video_editor/config.json`

## Agentic Workflow

Drop-and-go model — unchanged by GUI migration.

- Drop zone: `.incoming/`
- Output: `output/`
- Commands: `.\.venv\Scripts\python.exe src\cli.py list|compress|join`
- Protocol: `agent_instructions.md`

## Release

Single public repo ([Amirlabai/Video-Editor](https://github.com/Amirlabai/Video-Editor)). No separate releases repo.

- Build: `prod/gen_exe.py` → `prod/installers/ffmpegMagic_Setup_{version}.exe`
- CI: `.github/workflows/release-installer.yml` uploads `.exe` to tag `v{version}` and commits `latest.json`
- Update manifest: `https://raw.githubusercontent.com/Amirlabai/Video-Editor/main/latest.json`

## Conventions

- Run Python via `.\.venv\Scripts\python.exe`
- JSON API envelope: `{"status": "success"|"error", ...}`
- Windows GUI target; Linux/macOS CLI-only unless webview backend added later
