# Agent Protocol: Video Editor Drop & Go

Boss Man, use this protocol to handle video processing requests.

## Setup

1. Files go into `.incoming/`.
2. Results go into `output/`.

## Command Reference

### List Pending Files

```powershell
.\.venv\Scripts\python.exe src\cli.py list
```

### Compress All Videos (Default Settings)

```powershell
.\.venv\Scripts\python.exe src\cli.py compress
```

### Compress Specific File

```powershell
.\.venv\Scripts\python.exe src\cli.py compress --file "filename.mp4"
```

### High Quality (Lower CRF)

```powershell
.\.venv\Scripts\python.exe src\cli.py compress --crf 18 --preset slow
```

### Change Resolution

```powershell
.\.venv\Scripts\python.exe src\cli.py compress --resolution HD
```

### Force GPU

```powershell
.\.venv\Scripts\python.exe src\cli.py compress --gpu
```

### Join Videos

```powershell
.\.venv\Scripts\python.exe src\cli.py join
```

## Agent Guidelines

1. **Check First**: Always run `list` when user mentions "the files" or "in the folder".
2. **Batch Processing**: Default to processing all files in `.incoming/` unless a specific file is named.
3. **Quality Fallback**: If GPU fails, CLI automatically falls back to CPU (handled in `VideoProcessor`).
4. **Cleanup**: After successful processing, ask Boss Man if files in `.incoming/` should be cleared.
5. **GUI**: Human users run `src\web_app.py` — do not route agent automation through PyWebView.
