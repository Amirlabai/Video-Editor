"""
VideoJoiner class for joining multiple video files.
"""

import os
import subprocess
import time
import re
import logging
from typing import List, Optional

from utils.ffmpeg_paths import subprocess_env
from .VideoInfo import VideoInfo
from .FFmpegCommandBuilder import FFmpegCommandBuilder
from .progress_reporter import ProgressReporter, get_reporter
from .constants import (
    SUPPORTED_VIDEO_FORMATS, JOINED_OUTPUT_FILENAME, CONCAT_LIST_FILENAME,
    PROCESS_TERMINATION_TIMEOUT,
)

logger = logging.getLogger(__name__)


class VideoJoiner:
    """Handles joining multiple video files into one."""

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

    def _average_list(self, my_list: List[float]) -> float:
        return sum(my_list) / len(my_list) if my_list else 0

    def create_concat_file(self, video_files: List[str], folder_path: str) -> str:
        concat_file = os.path.join(folder_path, CONCAT_LIST_FILENAME).replace("\\", "/")
        with open(concat_file, "w", encoding="utf-8") as f:
            for video in video_files:
                abs_path = os.path.abspath(video)
                normalized_path = abs_path.replace("\\", "/")
                escaped_path = normalized_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        return concat_file

    def join_videos(
        self,
        concat_file: str,
        output_file: str,
        total_files: int,
        reporter: Optional[ProgressReporter] = None,
    ) -> bool:
        rep = get_reporter(reporter)
        self._cancel_requested = False
        ffmpeg_cmd = FFmpegCommandBuilder.build_concat_command(concat_file, output_file)

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
            rep.on_log("\nStarting FFmpeg to join videos...\n")
            rep.on_log(f"[0/{total_files}] Progress: Starting...\n")

            start_time = time.perf_counter()
            avg_time_diff = [0.0] * 10
            i = 0
            last_progress_msg = ""

            for line in process.stdout:
                if self._cancel_requested:
                    process.terminate()
                    try:
                        process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    rep.on_log("\nOperation cancelled by user\n")
                    self._current_process = None
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                            rep.on_log("\nPartial output file removed.\n")
                        except Exception:
                            pass
                    return False

                match = re.search(r"frame=\s*(\d+)", line)
                if match:
                    now = time.perf_counter()
                    elapsed = now - start_time
                    avg_time_diff[i] = elapsed
                    estimated_total_time = self._average_list(avg_time_diff) * total_files
                    elapsed_total_time = now - start_time
                    percentage = (elapsed_total_time / estimated_total_time) * 100 if estimated_total_time else 0
                    i = (i + 1) % 10
                    progress_message = f"[~/{total_files}] Progress: {percentage:.2f}% elapsed."
                    if progress_message != last_progress_msg:
                        last_progress_msg = progress_message
                        rep.on_log(progress_message + "\n")
                        rep.on_progress({"percent": percentage, "message": progress_message})

            process.wait()
            self._current_process = None

            if self._cancel_requested:
                return False

            if process.returncode == 0:
                rep.on_log(f"\nSuccessfully joined videos into: {output_file}\n")
                return True

            rep.on_log("\nFFmpeg failed! Check the output above for details.\n")
            return False

        except FileNotFoundError:
            self._current_process = None
            rep.on_log("FFmpeg not found! Make sure it's installed and added to PATH.\n")
            logger.error("FFmpeg not found")
            return False
        except Exception as e:
            self._current_process = None
            rep.on_log(f"\nError: {e}\n")
            logger.error(f"Error during join: {e}")
            return False

    def get_video_files(self, folder_path: str) -> List[str]:
        return sorted([
            os.path.join(folder_path, f).replace("\\", "/")
            for f in os.listdir(folder_path)
            if f.lower().endswith(SUPPORTED_VIDEO_FORMATS)
        ])
