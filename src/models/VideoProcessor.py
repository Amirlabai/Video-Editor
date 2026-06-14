"""
VideoProcessor class for handling video encoding operations.
"""

import subprocess
import re
import time
import os
import logging
from typing import List, Tuple, Optional
from threading import Thread

from utils.ffmpeg_paths import subprocess_env
from .FFmpegCommandBuilder import FFmpegCommandBuilder
from .progress_reporter import ProgressReporter, get_reporter
from .constants import (
    PROCESS_TERMINATION_TIMEOUT,
    HD_WIDTH, HD_HEIGHT, DEFAULT_CRF, DEFAULT_PRESET
)

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video encoding operations with progress tracking and error handling."""

    def __init__(self):
        self._current_process: Optional[subprocess.Popen] = None
        self._cancel_requested: bool = False

    def cancel(self) -> None:
        self._cancel_requested = True
        if self._current_process:
            try:
                self._current_process.terminate()
                logger.info("FFmpeg process terminated by user")
            except Exception as e:
                logger.error(f"Error terminating process: {e}")

    def _log(self, reporter: ProgressReporter, message: str) -> None:
        reporter.on_log(message if message.endswith("\n") else message + "\n")

    def _process_ffmpeg_output(
        self,
        process: subprocess.Popen,
        reporter: ProgressReporter,
        total_frames: Optional[int] = None,
        error_list: Optional[List[str]] = None,
        input_file: str = "",
        target_fps: Optional[float] = None,
        input_duration: Optional[float] = None,
    ) -> Tuple[int, List[str]]:
        if error_list is None:
            error_list = []

        start_time = time.perf_counter()
        tot_time = start_time
        current_frame = 0
        encoding_fps = 0.0
        output_duration = None

        output_total_frames = total_frames
        if target_fps is not None and input_duration is not None:
            output_total_frames = int(input_duration * target_fps)
        elif target_fps is not None and total_frames is not None:
            if hasattr(self, "_input_fps") and self._input_fps and self._input_fps > 0:
                fps_ratio = target_fps / self._input_fps
                output_total_frames = int(total_frames * fps_ratio)

        error_patterns = [
            r"\[error\]", r"Error", r"error", r"ERROR",
            r"Failed", r"failed", r"FAILED",
            r"Impossible", r"impossible",
            r"Could not", r"could not",
            r"Cannot", r"cannot",
            r"Invalid", r"invalid",
            r"not found", r"Not found", r"NOT FOUND",
            r"Permission denied", r"permission denied",
            r"No such file", r"no such file",
            r"Hardware is lacking", r"hardware is lacking",
            r"Function not implemented", r"function not implemented",
            r"moov atom not found", r"Invalid data found",
        ]

        progress_data = {}
        for line in process.stdout:
            if self._cancel_requested:
                logger.info("Cancel requested, terminating FFmpeg process")
                process.terminate()
                try:
                    process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                self._log(reporter, "\nOperation cancelled by user\n")
                return -1, error_list

            for pattern in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    error_list.append(line.strip())
                    break

            line = line.strip()
            if "=" in line and not line.startswith("ffmpeg") and not line.startswith("Input"):
                try:
                    key, value = line.split("=", 1)
                    progress_data[key] = value
                except ValueError:
                    pass

            if "progress" in progress_data:
                now = time.perf_counter()

                if "frame" in progress_data:
                    try:
                        current_frame = int(progress_data["frame"])
                    except (ValueError, TypeError):
                        pass

                if "fps" in progress_data:
                    try:
                        encoding_fps = float(progress_data["fps"])
                    except (ValueError, TypeError):
                        pass

                if "out_time_ms" in progress_data:
                    try:
                        output_time_ms = int(progress_data["out_time_ms"])
                        output_duration = output_time_ms / 1000000.0
                    except (ValueError, TypeError):
                        pass

                if output_total_frames and output_total_frames > 0:
                    percent = min(100.0, (current_frame / output_total_frames) * 100)
                elif output_duration and input_duration and input_duration > 0:
                    percent = min(100.0, (output_duration / input_duration) * 100)
                else:
                    percent = 0.0

                if encoding_fps > 0 and output_total_frames and output_total_frames > 0:
                    remaining_frames = max(0, output_total_frames - current_frame)
                    remaining_time = remaining_frames / encoding_fps
                elif output_duration is not None and input_duration and input_duration > 0:
                    remaining_time = max(0, input_duration - output_duration)
                else:
                    remaining_time = 0

                remaining_time = int(remaining_time)
                hours, minutes = divmod(remaining_time, 3600)
                minutes, seconds = divmod(minutes, 60)
                rem_str = f"{hours:02}:{minutes:02}:{seconds:02}"

                reporter.on_progress({
                    "frames_processed": current_frame,
                    "total_frames": output_total_frames or total_frames or 0,
                    "percent": percent,
                    "fps": encoding_fps,
                    "time_running_min": (now - tot_time) / 60,
                    "time_remaining": rem_str,
                    "Frames Processed:": f"{current_frame}/{output_total_frames or total_frames or 0}",
                    "Progress:": f"{percent:.2f}%",
                    "Average Frame Rate:": f"{encoding_fps:.1f} fps",
                    "Time Running:": f"{(now - tot_time) / 60:.2f} min",
                    "Time Remaining:": rem_str,
                })

                if progress_data.get("progress") == "end":
                    break
                progress_data = {}

        return_code = process.wait()
        return return_code, error_list

    def scale_video_cpu(
        self,
        input_file: str,
        output_file: str,
        total_frames: Optional[int] = None,
        reporter: Optional[ProgressReporter] = None,
        ratio: bool = False,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET,
        threads: int = 0,
        fps: Optional[float] = None,
        input_duration: Optional[float] = None,
        input_fps: Optional[float] = None,
    ) -> bool:
        rep = get_reporter(reporter)
        self._cancel_requested = False

        if input_duration is None or input_fps is None:
            from .VideoInfo import VideoInfo
            video_info = VideoInfo(input_file)
            if input_duration is None:
                input_duration = video_info.get_duration()
            if input_fps is None:
                input_fps = video_info.fps

        if input_fps:
            self._input_fps = input_fps

        try:
            from .VideoInfo import VideoInfo
            vi = VideoInfo(input_file)
            input_w, input_h = vi.get_fps_and_size()[1:] if vi.get_fps_and_size() else ("?", "?")
            codec = vi.codec if vi.codec else "Unknown"
            self._log(rep, f"Resolution: {input_w}x{input_h} -> {xaxis}x{yaxis}\n")
            self._log(rep, f"Input Codec: {codec}\nSettings: CRF={crf}, Preset={preset}\n")
        except Exception as e:
            logger.warning(f"Could not log resolution: {e}")

        ffmpeg_cmd = FFmpegCommandBuilder.build_scale_command_cpu(
            input_file, output_file, xaxis, yaxis, crf, preset, threads, fps=fps
        )
        error_list: List[str] = []

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                env=subprocess_env(),
            )
            self._current_process = process

            threading_info = f" with {threads} threads" if threads > 0 else " (auto threading)"
            self._log(rep, f"Starting FFmpeg{threading_info}...\n")

            return_code, error_list = self._process_ffmpeg_output(
                process, rep, total_frames, error_list, input_file,
                target_fps=fps, input_duration=input_duration,
            )
            self._current_process = None

            if self._cancel_requested or return_code == -1:
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        self._log(rep, "\nPartial output file removed.\n")
                    except Exception as e:
                        logger.warning(f"Could not remove partial file: {e}")
                self._log(rep, "\nOperation cancelled by user.\n")
                return False

            return self._handle_process_result(
                return_code, error_list, output_file, rep, input_file
            )

        except FileNotFoundError:
            self._current_process = None
            self._log(rep, "FFmpeg not found! Make sure it's installed and added to PATH.\n")
            logger.error("FFmpeg not found")
            return False
        except Exception as e:
            self._current_process = None
            logger.error(f"Error during CPU encoding: {e}")
            self._log(rep, f"\nError: {e}\n")
            return False

    def scale_video_gpu(
        self,
        input_file: str,
        output_file: str,
        total_frames: Optional[int] = None,
        reporter: Optional[ProgressReporter] = None,
        ratio: bool = False,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET,
        fps: Optional[float] = None,
        input_duration: Optional[float] = None,
        input_fps: Optional[float] = None,
    ) -> bool:
        rep = get_reporter(reporter)
        self._cancel_requested = False

        if input_duration is None or input_fps is None:
            from .VideoInfo import VideoInfo
            video_info = VideoInfo(input_file)
            if input_duration is None:
                input_duration = video_info.get_duration()
            if input_fps is None:
                input_fps = video_info.fps

        if input_fps:
            self._input_fps = input_fps

        try:
            from .VideoInfo import VideoInfo
            vi = VideoInfo(input_file)
            input_w, input_h = vi.get_fps_and_size()[1:] if vi.get_fps_and_size() else ("?", "?")
            codec = vi.codec if vi.codec else "Unknown"
            self._log(rep, f"Resolution: {input_w}x{input_h} -> {xaxis}x{yaxis}\n")
            self._log(rep, f"Input Codec: {codec}\nSettings: CRF={crf}, Preset={preset}\n")
        except Exception as e:
            logger.warning(f"Could not log resolution: {e}")

        ffmpeg_cmd = FFmpegCommandBuilder.build_scale_command_gpu(
            input_file, output_file, xaxis, yaxis, crf, preset, fps=fps
        )
        error_list: List[str] = []

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                env=subprocess_env(),
            )
            self._current_process = process
            self._log(rep, "Starting FFmpeg with GPU acceleration (NVENC)...\n")

            return_code, error_list = self._process_ffmpeg_output(
                process, rep, total_frames, error_list, input_file,
                target_fps=fps, input_duration=input_duration,
            )
            self._current_process = None

            if self._cancel_requested or return_code == -1:
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        self._log(rep, "\nPartial output file removed.\n")
                    except Exception as e:
                        logger.warning(f"Could not remove partial file: {e}")
                self._log(rep, "\nOperation cancelled by user.\n")
                return False

            nvenc_dll_error = any(
                "Cannot load nvEncodeAPI64.dll" in err or "nvEncodeAPI" in err
                for err in error_list
            )

            if nvenc_dll_error:
                logger.warning("NVENC DLL error detected, falling back to CPU encoding")
                self._log(rep, "\nGPU encoding failed, falling back to CPU...\n")
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except Exception:
                        pass
                return self.scale_video_cpu(
                    input_file, output_file, total_frames, rep,
                    ratio, xaxis, yaxis, crf, preset, threads=0, fps=fps,
                    input_duration=input_duration, input_fps=input_fps,
                )

            return self._handle_process_result(
                return_code, error_list, output_file, rep, input_file
            )

        except FileNotFoundError:
            self._current_process = None
            self._log(rep, "FFmpeg not found! Make sure it's installed and added to PATH.\n")
            logger.error("FFmpeg not found")
            return False
        except Exception as e:
            self._current_process = None
            logger.error(f"Error during GPU encoding: {e}")
            self._log(rep, f"\nError: {e}\n")
            return False

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def _handle_process_result(
        self,
        return_code: int,
        error_list: List[str],
        output_file: str,
        reporter: ProgressReporter,
        input_file: Optional[str] = None,
    ) -> bool:
        if return_code == 0:
            self._log(reporter, f"\nSuccessfully processed: {output_file}\n")

            if input_file and os.path.exists(input_file) and os.path.exists(output_file):
                try:
                    input_size = os.path.getsize(input_file)
                    output_size = os.path.getsize(output_file)
                    size_reduction = input_size - output_size
                    reduction_percent = (size_reduction / input_size * 100) if input_size > 0 else 0

                    self._log(reporter, "\nFile Size Comparison:\n")
                    self._log(reporter, f"  Input:  {VideoProcessor.format_file_size(input_size)}\n")
                    self._log(reporter, f"  Output: {VideoProcessor.format_file_size(output_size)}\n")
                    if reduction_percent > 0:
                        self._log(reporter, f"  Reduction: {VideoProcessor.format_file_size(size_reduction)} ({reduction_percent:.1f}% smaller)\n")
                    elif reduction_percent < 0:
                        self._log(reporter, f"  Increase: {VideoProcessor.format_file_size(abs(size_reduction))} ({abs(reduction_percent):.1f}% larger)\n")
                    else:
                        self._log(reporter, "  No size change\n")
                except Exception as e:
                    logger.warning(f"Could not get file sizes: {e}")

            if error_list:
                self._log(reporter, f"\nWarnings detected: {len(error_list)} warning(s)\n")
                for error in error_list[:5]:
                    self._log(reporter, f"  - {error}\n")
                if len(error_list) > 5:
                    self._log(reporter, f"  ... and {len(error_list) - 5} more\n")
            return True

        error_msg = self._get_ffmpeg_error_code(return_code)
        self._log(reporter, f"\nFFmpeg failed with return code {return_code}: {error_msg}\n")
        if error_list:
            is_moov_error = any("moov atom not found" in err for err in error_list)
            is_invalid_data = any("Invalid data found" in err for err in error_list)
            if is_moov_error:
                self._log(reporter, "  ! HINT: Input file may be corrupted (moov atom not found).\n")
            if is_invalid_data:
                self._log(reporter, "  ! HINT: Input file contains invalid data.\n")
            for error in error_list:
                self._log(reporter, f"  - {error}\n")
        return False

    @staticmethod
    def _get_ffmpeg_error_code(return_code: int) -> str:
        error_codes = {
            0: "Success", 1: "Unknown error", -1: "Process terminated",
            -2: "Invalid argument", -3: "No such file or directory",
            -4: "Permission denied", -5: "I/O error", -6: "No space left on device",
            -7: "Out of memory", -8: "Invalid data found",
        }
        return error_codes.get(return_code, f"Unknown error code: {return_code}")
