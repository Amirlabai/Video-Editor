# Bundled FFmpeg (Windows)

ffmpegMagic can ship `ffmpeg.exe` and `ffprobe.exe` inside the Windows installer.

## License and credit

Read [NOTICE.txt](NOTICE.txt). FFmpeg is from https://ffmpeg.org — credit the project
and comply with LGPL/GPL terms for the build you redistribute.

## Fetch before building the installer

```powershell
.\.venv\Scripts\python.exe scripts\fetch_ffmpeg.py
.\.venv\Scripts\python.exe prod\gen_exe.py
```

`gen_exe.py` runs the fetch script automatically if binaries are missing.

## Layout

```
vendor/ffmpeg/win64/
  ffmpeg.exe
  ffprobe.exe
  *.dll          # shared build runtime DLLs
  LICENSE.txt    # from upstream archive
  SOURCE.txt     # download URL and version metadata
```

These files are gitignored (large binaries). Development without fetch falls back
to `ffmpeg` / `ffprobe` on PATH.

## Upstream

GPL shared Windows build from [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds)
(release tag `latest`, archive `ffmpeg-master-latest-win64-gpl-shared.zip`).
