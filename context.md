# Project Context: Video-Editor

## Overview
A lightweight video processing tool offering scaling and joining capabilities via FFmpeg. Built with Python and CustomTkinter.

## Architecture
- `src/VideoScalerInterface.py`: Main GUI entry point.
- `src/models/VideoProcessor.py`: Core logic for FFmpeg subprocess management (refactored for headless).
- `src/models/VideoJoiner.py`: Logic for merging videos (refactored for headless).
- `src/cli.py`: CLI wrapper for agentic processing.
- `src/models/ConfigManager.py`: Handles persistent settings.

## Technology Stack
- **Language**: Python 3.11+
- **GUI**: CustomTkinter
- **Processing**: FFmpeg

## Agentic Workflow
The project follows a "drop and go" model.

### Skill Location:
- `.agents/workflows/video-proccesing.md`

### Commands:
- `list`: Check `.incoming/` contents.
- `compress`: Scale down videos.
- `join`: Merge all files in `.incoming/` into one.
