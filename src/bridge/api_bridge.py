"""
PyWebView API bridge for ffmpegMagic.
"""

import functools
import json
import logging
import multiprocessing
import os
import platform
import shutil
import subprocess
import sys
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.ConfigManager import get_config_manager
from models.VideoInfo import VideoInfo
from models.VideoJoiner import VideoJoiner
from models.VideoProcessor import VideoProcessor
from models.constants import (
    CRF_MAX, CRF_MIN, HD_HEIGHT, HD_WIDTH, FHD_HEIGHT, FHD_WIDTH,
    JOINED_OUTPUT_FILENAME, PRESET_OPTIONS, SUPPORTED_VIDEO_FORMATS,
    UHD_4K_HEIGHT, UHD_4K_WIDTH,
)
from models.progress_reporter import ProgressReporter
from utils import update_check
from utils.core_functions import asset_file_uri
from utils.ffmpeg_paths import check_ffmpeg_available, get_ffmpeg_exe, get_ffmpeg_info, subprocess_env

logger = logging.getLogger(__name__)

_UI_LOG_SKIP = frozenset({"set_window", "compress_get_status"})


def _looks_like_path(value: str) -> bool:
    if len(value) <= 1:
        return False
    if value[0] in "/\\":
        return True
    if len(value) >= 3 and value[1] == ":" and value[2] in "/\\":
        return True
    return False


def _format_ui_arg(value: Any) -> str:
    if value is None or isinstance(value, (bool, int, float)):
        return str(value)
    if isinstance(value, str):
        if _looks_like_path(value):
            return os.path.basename(value) or value
        if len(value) > 80:
            return value[:77] + "..."
        return value
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(isinstance(x, str) for x in value):
            names = [os.path.basename(x) if _looks_like_path(x) else x for x in value[:5]]
            extra = f" +{len(value) - 5} more" if len(value) > 5 else ""
            return f"[{', '.join(names)}{extra}]"
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        keys = list(value.keys())[:6]
        suffix = "..." if len(value) > 6 else ""
        return "{" + ", ".join(keys) + suffix + "}"
    text = repr(value)
    return text[:80] + ("..." if len(text) > 80 else "")


def _format_ui_args(args: tuple, kwargs: dict) -> str:
    parts = [_format_ui_arg(a) for a in args]
    parts.extend(f"{k}={_format_ui_arg(v)}" for k, v in kwargs.items())
    return ", ".join(parts)


def _wrap_ui_logging(cls):
    """Wrap public methods on cls and its bases (MRO order, first definition wins)."""
    wrapped: set[str] = set()
    for base in cls.__mro__:
        if base is object:
            continue
        for name, attr in base.__dict__.items():
            if name in wrapped or name.startswith("_") or name in _UI_LOG_SKIP or not callable(attr):
                continue
            wrapped.add(name)

            @functools.wraps(attr)
            def wrapper(self, *args, _method=attr, **kwargs):
                try:
                    detail = _format_ui_args(args, kwargs)
                    logger.info("UI %s(%s)", _method.__name__, detail)
                except Exception:
                    logger.debug("UI log format failed for %s", _method.__name__, exc_info=True)
                    logger.info("UI %s()", _method.__name__)
                return _method(self, *args, **kwargs)

            setattr(cls, name, wrapper)
    return cls


FPS_OPTIONS = ["12", "24", "25", "29.97", "30", "50", "60", "120"]
RESOLUTION_OPTIONS = ["HD (1280x720)", "FHD (1920x1080)", "4K (3840x2160)"]
RESOLUTION_MAP = {
    "HD (1280x720)": ("HD", str(HD_WIDTH), str(HD_HEIGHT)),
    "FHD (1920x1080)": ("FHD", str(FHD_WIDTH), str(FHD_HEIGHT)),
    "4K (3840x2160)": ("4K", str(UHD_4K_WIDTH), str(UHD_4K_HEIGHT)),
}
CRF_OPTIONS = [str(i) for i in range(CRF_MIN, CRF_MAX + 1)]


def _build_file_types(extensions: str) -> tuple[str, ...]:
    """pywebview filter strings: 'Label (*.ext;*.ext2)'. Empty input -> () (no filter, all files)."""
    ext_list = [e.strip() for e in extensions.split(";") if e.strip()]
    if not ext_list:
        return tuple()
    return (f"Videos ({';'.join(ext_list)})",)


def _normalize_dialog_dir(initial_dir: str) -> str:
    path = (initial_dir or "").strip()
    if path and os.path.isdir(path):
        return path
    return ""


class BridgeProgressReporter:
    """Pushes progress to the web UI via evaluate_js."""

    def __init__(self, api: "VideoEditorApi", job_id: str, job_type: str):
        self._api = api
        self._job_id = job_id
        self._job_type = job_type

    def _emit(self, event: str, payload: dict) -> None:
        self._api._emit_event(event, {**payload, "job_id": self._job_id})

    def on_progress(self, metrics: dict) -> None:
        if self._job_type == "compress":
            self._emit("compress_progress", metrics)
        else:
            self._emit("join_progress", metrics)

    def on_log(self, line: str) -> None:
        if self._job_type == "compress":
            self._emit("compress_log", {"line": line})
        else:
            self._emit("join_log", {"line": line})

    def on_file_status(self, index: int, status: str) -> None:
        self._emit("compress_file_status", {"index": index, "status": status})


@_wrap_ui_logging
class VideoEditorApi:
    """JSON API exposed to JavaScript as window.pywebview.api."""

    def __init__(self):
        self._window = None
        self._config = get_config_manager()
        self._processor = VideoProcessor()
        self._joiner = VideoJoiner()
        self._jobs_lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._job_threads: Dict[str, threading.Thread] = {}

    def set_window(self, window) -> None:
        self._window = window

    def _ok(self, payload: Optional[dict] = None) -> dict:
        base = {"status": "success"}
        if payload:
            base.update(payload)
        return base

    def _err(self, message: str) -> dict:
        return {"status": "error", "message": str(message)}

    def _emit_event(self, handler: str, payload: dict) -> None:
        if not self._window:
            return
        try:
            js = f"if (window.{handler}) window.{handler}({json.dumps(payload)});"
            self._window.evaluate_js(js)
        except Exception as e:
            logger.debug(f"evaluate_js failed: {e}")

    def _check_ffmpeg(self) -> bool:
        return check_ffmpeg_available()

    def _check_gpu_available(self) -> bool:
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(
                [get_ffmpeg_exe(), "-encoders"],
                capture_output=True,
                text=True,
                timeout=15,
                startupinfo=startupinfo,
                env=subprocess_env(),
            )
            return "h264_nvenc" in result.stdout
        except Exception:
            return False

    def prepare_startup(self) -> dict:
        if not self._check_ffmpeg():
            return self._err(
                "FFmpeg not found. Install FFmpeg, run scripts/fetch_ffmpeg.py, or reinstall the application."
            )
        gpu = self._check_gpu_available()
        return self._ok({"gpu_available": gpu, "ffmpeg_bundled": get_ffmpeg_info().get("bundled", False)})

    def get_initial_data(self) -> dict:
        from _version import __version__
        crf, preset, resolution = self._config.get_encoding_settings()
        use_gpu, use_all_cores = self._config.get_performance_settings()
        return self._ok({
            "version": __version__,
            "app_name": "ffmpegMagic",
            "gpu_available": self._check_gpu_available(),
            "cpu_cores": multiprocessing.cpu_count(),
            "encoding_defaults": {
                "crf": crf,
                "preset": preset,
                "resolution": resolution,
            },
            "performance_defaults": {
                "use_gpu": use_gpu,
                "use_all_cores": use_all_cores,
                "cap_cpu_50": self._config.get_cpu_cap_setting(),
            },
        })

    def get_asset_uri(self, relative_path: str) -> dict:
        try:
            return self._ok({"uri": asset_file_uri(relative_path)})
        except Exception as e:
            return self._err(str(e))

    def log_js(self, level: str, message: str) -> dict:
        log_fn = getattr(logger, level.lower(), logger.info)
        log_fn(f"[JS] {message}")
        return self._ok()

    def pick_files(self, initial_dir: str = "", extensions: str = "") -> dict:
        if not self._window:
            return self._err("Window not ready")
        try:
            import webview
            directory = _normalize_dialog_dir(initial_dir)
            file_types = _build_file_types(extensions)
            files = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                directory=directory,
                allow_multiple=True,
                file_types=file_types,
            )
            paths = list(files) if files else []
            if paths:
                self._config.set_last_input_folder(os.path.dirname(paths[0]))
            return self._ok({"paths": paths})
        except Exception as e:
            logger.exception("pick_files failed")
            return self._err(str(e))

    def pick_folder(self, initial_dir: str = "", title: str = "", folder_kind: str = "") -> dict:
        if not self._window:
            return self._err("Window not ready")
        try:
            import webview
            directory = _normalize_dialog_dir(initial_dir)
            folders = self._window.create_file_dialog(
                webview.FOLDER_DIALOG,
                directory=directory,
            )
            path = folders[0] if folders else None
            if path and folder_kind:
                if folder_kind == "input":
                    self._config.set_last_input_folder(path)
                elif folder_kind == "output":
                    self._config.set_last_output_folder(path)
                elif folder_kind == "join_input":
                    self._config.set_last_join_input_folder(path)
                elif folder_kind == "join_output":
                    self._config.set_last_join_output_folder(path)
            return self._ok({"path": path, "title": title})
        except Exception as e:
            logger.exception("pick_folder failed")
            return self._err(str(e))

    def open_path_in_explorer(self, path: str) -> dict:
        try:
            p = path or self._config.get_config_dir_path()
            if platform.system() == "Windows":
                os.startfile(p)
            elif platform.system() == "Darwin":
                subprocess.run(["open", p], check=False)
            else:
                subprocess.run(["xdg-open", p], check=False)
            return self._ok()
        except Exception as e:
            return self._err(str(e))

    def open_config_in_editor(self) -> dict:
        if self._config.open_config_in_editor():
            return self._ok()
        return self._err("Could not open configuration file")

    def copy_to_clipboard(self, text: str) -> dict:
        try:
            if self._window:
                self._window.evaluate_js(f"navigator.clipboard.writeText({json.dumps(text)})")
            return self._ok()
        except Exception:
            return self._err("Clipboard copy failed")

    def compress_get_options(self) -> dict:
        crf, preset, resolution = self._config.get_encoding_settings()
        use_gpu, use_all_cores = self._config.get_performance_settings()
        cap_cpu_50 = self._config.get_cpu_cap_setting()
        target_fps = self._config.get_target_fps()
        fps_default = FPS_OPTIONS[0]
        if target_fps is not None:
            fps_default = min(FPS_OPTIONS, key=lambda x: abs(float(x) - target_fps))
        res_label = {
            "HD": RESOLUTION_OPTIONS[0],
            "FHD": RESOLUTION_OPTIONS[1],
            "4K": RESOLUTION_OPTIONS[2],
        }.get(resolution, RESOLUTION_OPTIONS[1])
        return self._ok({
            "fps_options": FPS_OPTIONS,
            "resolution_options": RESOLUTION_OPTIONS,
            "preset_options": PRESET_OPTIONS,
            "crf_options": CRF_OPTIONS,
            "crf_min": CRF_MIN,
            "crf_max": CRF_MAX,
            "defaults": {
                "fps": fps_default,
                "resolution": res_label,
                "crf": crf,
                "preset": preset,
                "output_folder": self._config.get_last_output_folder() or "",
                "use_gpu": use_gpu,
                "use_all_cores": use_all_cores,
                "cap_cpu_50": cap_cpu_50,
            },
            "last_input_folder": self._config.get_last_input_folder(),
            "gpu_available": self._check_gpu_available(),
            "cpu_cores": multiprocessing.cpu_count(),
        })

    def _video_to_dict(self, path: str, is_vertical: bool = False) -> dict:
        vi = VideoInfo(path)
        w, h = vi.width or 0, vi.height or 0
        if is_vertical and w and h:
            w, h = h, w
        duration = vi.get_duration()
        size = os.path.getsize(path) if os.path.exists(path) else 0
        orientation = "Vertical" if is_vertical else "Horizontal"
        return {
            "path": path,
            "file": os.path.basename(path),
            "resolution": f"{vi.width}x{vi.height}" if vi.width else "?",
            "fps": f"{vi.fps:.2f}" if vi.fps else "?",
            "codec": vi.codec or "?",
            "duration": f"{duration:.1f}s" if duration else "?",
            "size": VideoProcessor.format_file_size(size),
            "orientation": orientation,
            "is_vertical": is_vertical,
            "status": "Pending",
        }

    def compress_probe_videos(self, paths: List[str]) -> dict:
        items = []
        for p in paths:
            try:
                items.append(self._video_to_dict(p))
            except Exception as e:
                items.append({"path": p, "file": os.path.basename(p), "status": "Error", "error": str(e)})
        return self._ok({"videos": items})

    def compress_start(self, payload: dict) -> dict:
        with self._jobs_lock:
            for job in self._jobs.values():
                if job.get("type") == "compress" and job.get("state") == "running":
                    return self._err("Compress job already running")

        videos = payload.get("videos", [])
        settings = payload.get("settings", {})
        output_folder = settings.get("output_folder", "")
        if not videos:
            return self._err("No videos in queue")
        if not output_folder:
            return self._err("Select an output folder")

        os.makedirs(output_folder, exist_ok=True)
        self._config.set_last_output_folder(output_folder)
        self._config.set_performance_settings(
            settings.get("use_gpu", False),
            settings.get("use_all_cores", False),
            settings.get("cap_cpu_50", False),
        )
        fps_val = settings.get("fps")
        if fps_val:
            try:
                self._config.set_target_fps(float(fps_val))
            except ValueError:
                pass
        res_key = settings.get("resolution", RESOLUTION_OPTIONS[1])
        res_name, width, height = RESOLUTION_MAP.get(res_key, ("FHD", str(FHD_WIDTH), str(FHD_HEIGHT)))
        if settings.get("width"):
            width = str(settings["width"])
        if settings.get("height"):
            height = str(settings["height"])
        self._config.set_encoding_settings(
            str(settings.get("crf", "30")),
            settings.get("preset", "ultrafast"),
            res_name,
        )

        job_id = str(uuid.uuid4())
        with self._jobs_lock:
            self._jobs[job_id] = {
                "type": "compress",
                "state": "running",
                "total": len(videos),
                "processed": 0,
            }

        thread = threading.Thread(
            target=self._run_compress_job,
            args=(job_id, videos, settings, output_folder, width, height),
            daemon=True,
        )
        self._job_threads[job_id] = thread
        thread.start()
        return self._ok({"job_id": job_id})

    def _run_compress_job(
        self, job_id: str, videos: list, settings: dict,
        output_folder: str, width: str, height: str,
    ) -> None:
        reporter = BridgeProgressReporter(self, job_id, "compress")
        use_gpu = settings.get("use_gpu", False)
        use_all_cores = settings.get("use_all_cores", False)
        cap_cpu_50 = settings.get("cap_cpu_50", False)
        cpu_cores = multiprocessing.cpu_count()
        threads = cpu_cores // 2 if cap_cpu_50 else (cpu_cores if use_all_cores else 0)
        crf = str(settings.get("crf", "30"))
        preset = settings.get("preset", "ultrafast")
        fps = settings.get("fps")
        target_fps = float(fps) if fps else None

        reporter.on_progress({
            "Total Files:": str(len(videos)),
            "Files Processed:": "0",
            "Current File:": "",
        })

        processed = 0
        for index, item in enumerate(videos):
            with self._jobs_lock:
                if self._jobs.get(job_id, {}).get("state") == "cancelled":
                    break

            path = item.get("path", "")
            is_vertical = item.get("is_vertical", False)
            w, h = width, height
            if is_vertical:
                w, h = height, width

            reporter.on_file_status(index, "Processing")
            reporter.on_progress({"Current File:": os.path.basename(path)})

            vi = VideoInfo(path)
            base, ext = os.path.splitext(os.path.basename(path))
            out_name = f"{base}_scaled{ext}"
            output_file = os.path.join(output_folder, out_name)

            ok = False
            if use_gpu and self._check_gpu_available():
                ok = self._processor.scale_video_gpu(
                    path, output_file,
                    total_frames=vi.get_total_frames(),
                    reporter=reporter,
                    xaxis=w, yaxis=h,
                    crf=crf, preset=preset, fps=target_fps,
                    input_duration=vi.get_duration(), input_fps=vi.fps,
                )
            else:
                ok = self._processor.scale_video_cpu(
                    path, output_file,
                    total_frames=vi.get_total_frames(),
                    reporter=reporter,
                    xaxis=w, yaxis=h,
                    crf=crf, preset=preset, threads=threads, fps=target_fps,
                    input_duration=vi.get_duration(), input_fps=vi.fps,
                )

            status = "Completed" if ok else "Error"
            reporter.on_file_status(index, status)
            if ok:
                processed += 1
                reporter.on_progress({"Files Processed:": str(processed)})
            else:
                with self._jobs_lock:
                    if self._jobs.get(job_id, {}).get("state") == "cancelled":
                        break

        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            cancelled = job.get("state") == "cancelled"
            job["state"] = "cancelled" if cancelled else "done"
            job["processed"] = processed

        self._emit_event("compress_complete", {
            "job_id": job_id,
            "processed": processed,
            "cancelled": cancelled,
        })

    def compress_cancel(self, job_id: str = "") -> dict:
        with self._jobs_lock:
            if job_id:
                if job_id not in self._jobs:
                    return self._err("Job not found")
                self._jobs[job_id]["state"] = "cancelled"
            else:
                for job in self._jobs.values():
                    if job.get("type") == "compress" and job.get("state") == "running":
                        job["state"] = "cancelled"
        self._processor.cancel()
        return self._ok()

    def compress_get_status(self, job_id: str) -> dict:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
        if not job:
            return self._err("Job not found")
        return self._ok(job)

    def join_scan_folder(self, folder_path: str) -> dict:
        if not folder_path or not os.path.isdir(folder_path):
            return self._err("Invalid folder")
        files = self._joiner.get_video_files(folder_path)
        compatible = VideoInfo.check_compatibility(files) if len(files) >= 2 else False
        return self._ok({
            "files": files,
            "count": len(files),
            "compatible": compatible,
        })

    def join_start(self, input_folder: str, output_folder: str = "") -> dict:
        with self._jobs_lock:
            for job in self._jobs.values():
                if job.get("type") == "join" and job.get("state") == "running":
                    return self._err("Join job already running")

        if not input_folder:
            return self._err("Select input folder")
        self._config.set_last_join_input_folder(input_folder)
        out = output_folder or input_folder
        if output_folder:
            self._config.set_last_join_output_folder(output_folder)

        files = self._joiner.get_video_files(input_folder)
        if len(files) < 2:
            return self._err("Need at least two video files")
        if not VideoInfo.check_compatibility(files):
            return self._err("Videos have incompatible properties")

        job_id = str(uuid.uuid4())
        with self._jobs_lock:
            self._jobs[job_id] = {"type": "join", "state": "running"}

        thread = threading.Thread(
            target=self._run_join_job,
            args=(job_id, input_folder, out, files),
            daemon=True,
        )
        self._job_threads[job_id] = thread
        thread.start()
        return self._ok({"job_id": job_id})

    def _run_join_job(self, job_id: str, input_folder: str, output_folder: str, files: list) -> None:
        reporter = BridgeProgressReporter(self, job_id, "join")
        concat_file = self._joiner.create_concat_file(files, input_folder)
        output_file = os.path.join(output_folder, JOINED_OUTPUT_FILENAME)
        try:
            ok = self._joiner.join_videos(concat_file, output_file, len(files), reporter=reporter)
        finally:
            if os.path.exists(concat_file):
                try:
                    os.remove(concat_file)
                except OSError:
                    pass
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            cancelled = job.get("state") == "cancelled"
            job["state"] = "cancelled" if cancelled else ("done" if ok else "error")
        self._emit_event("join_complete", {
            "job_id": job_id,
            "success": ok and not cancelled,
            "cancelled": cancelled,
            "output": output_file if ok and not cancelled else "",
        })

    def join_cancel(self, job_id: str = "") -> dict:
        with self._jobs_lock:
            if job_id:
                if job_id not in self._jobs:
                    return self._err("Job not found")
                self._jobs[job_id]["state"] = "cancelled"
            else:
                for job in self._jobs.values():
                    if job.get("type") == "join" and job.get("state") == "running":
                        job["state"] = "cancelled"
        self._joiner.cancel()
        return self._ok()

    def settings_get_summary(self) -> dict:
        use_gpu, use_all_cores = self._config.get_performance_settings()
        crf, preset, resolution = self._config.get_encoding_settings()
        return self._ok({
            "performance": {
                "use_gpu": use_gpu,
                "use_all_cores": use_all_cores,
                "cap_cpu_50": self._config.get_cpu_cap_setting(),
            },
            "encoding": {"crf": crf, "preset": preset, "resolution": resolution},
            "folders": {
                "last_input": self._config.get_last_input_folder() or "(none)",
                "last_output": self._config.get_last_output_folder() or "(none)",
                "last_join_input": self._config.get_last_join_input_folder() or "(none)",
                "last_join_output": self._config.get_last_join_output_folder() or "(none)",
            },
        })

    def settings_get_path(self) -> dict:
        return self._ok({
            "file": self._config.get_config_file_path(),
            "directory": self._config.get_config_dir_path(),
        })

    def get_ffmpeg_notice(self) -> dict:
        return self._ok(get_ffmpeg_info())

    def check_for_updates(self, force: bool = False) -> dict:
        from _version import __version__
        cfg = self._config.get_raw_config()
        result = update_check.check_for_update(__version__, cfg, force=bool(force))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cfg.setdefault("updates", {})["update_last_check_at"] = now
        self._config.save_raw_config()
        return self._ok(result)

    def open_update_download(self, url: str) -> dict:
        url = (url or "").strip()
        if not url:
            return self._err("No download URL provided")
        if sys.platform == "win32":
            os.startfile(url)
        else:
            webbrowser.open(url)
        return self._ok()

    def dismiss_update_notice(self, latest_version: str, action: str = "later") -> dict:
        cfg = self._config.get_raw_config()
        update_check.apply_snooze(cfg, action, latest_version)
        self._config.save_raw_config()
        return self._ok()

    def exit_app(self) -> dict:
        self.compress_cancel()
        self.join_cancel()
        for thread in list(self._job_threads.values()):
            if thread.is_alive():
                thread.join(timeout=2)
        if self._window:
            self._window.destroy()
        sys.exit(0)
