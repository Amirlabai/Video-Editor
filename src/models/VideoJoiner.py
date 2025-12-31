"""
VideoJoiner class for joining multiple video files.
"""

import os
import subprocess
import time
import re
import logging
from typing import List, Optional
from pathlib import Path

from .VideoInfo import VideoInfo
from .FFmpegCommandBuilder import FFmpegCommandBuilder
from .constants import (
    SUPPORTED_VIDEO_FORMATS, JOINED_OUTPUT_FILENAME, CONCAT_LIST_FILENAME,
    PROCESS_TERMINATION_TIMEOUT, CANCELLATION_MESSAGE_DELAY
)

logger = logging.getLogger(__name__)


class VideoJoiner:
    """Handles joining multiple video files into one."""
    
    def __init__(self):
        """Initialize VideoJoiner."""
        self._current_process: Optional[subprocess.Popen] = None
        self._cancel_requested: bool = False
    
    def cancel(self) -> None:
        """Cancel the current joining operation."""
        self._cancel_requested = True
        if self._current_process:
            try:
                self._current_process.terminate()
                logger.info("FFmpeg process terminated by user")
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
    
    def _average_list(self, my_list: List[float]) -> float:
        """Calculate average of a list."""
        return sum(my_list) / len(my_list) if my_list else 0
    
    def create_concat_file(self, video_files: List[str], folder_path: str) -> str:
        """Create FFmpeg concat file with properly escaped paths.
        
        Args:
            video_files: List of video file paths
            folder_path: Folder to save concat file in
            
        Returns:
            Path to the created concat file
        """
        concat_file = os.path.join(folder_path, CONCAT_LIST_FILENAME).replace("\\", "/")
        
        with open(concat_file, "w", encoding="utf-8") as f:
            for video in video_files:
                # Convert to absolute path and normalize
                abs_path = os.path.abspath(video)
                # Use forward slashes for Windows compatibility with FFmpeg
                normalized_path = abs_path.replace("\\", "/")
                # Escape single quotes in path (FFmpeg concat format: ' becomes '\'')
                escaped_path = normalized_path.replace("'", "'\\''")
                # Write in FFmpeg concat format
                f.write(f"file '{escaped_path}'\n")
        
        return concat_file
    
    def join_videos(
        self,
        concat_file: str,
        output_file: str,
        total_files: int,
        output_text,
        root
    ) -> None:
        """Join videos using FFmpeg concat demuxer.
        
        Args:
            concat_file: Path to concat list file
            output_file: Output video file path
            total_files: Total number of files being joined
            output_text: Tkinter Text widget for output
            root: Tkinter root window
        """
        self._cancel_requested = False
        
        # Build FFmpeg command
        ffmpeg_cmd = FFmpegCommandBuilder.build_concat_command(concat_file, output_file)
        
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            self._current_process = process

            output_text.insert("end", "\n🚀 Starting FFmpeg to join videos...\n")
            output_text.see("end")

            progress_line_index = output_text.index("end")
            output_text.insert("end", f"🟢 [0/{total_files}] Progress: Starting...\n")
            output_text.see("end")

            start_time = time.perf_counter()
            avg_time_diff = [0] * 10
            i = 0

            for line in process.stdout:
                # Check for cancellation
                if self._cancel_requested:
                    process.terminate()
                    try:
                        process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    output_text.insert("end", "\n⚠️ Operation cancelled by user\n")
                    output_text.see("end")
                    self._current_process = None
                    # Clean up partial output file
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                            output_text.insert("end", f"\n🗑️ Partial output file removed.\n")
                        except Exception:
                            pass
                    # Close window after showing cancellation message
                    root.after(CANCELLATION_MESSAGE_DELAY, lambda: (
                        __import__('tkinter.messagebox').showinfo("Cancelled", "Operation was cancelled."),
                        root.destroy()
                    ))
                    return
                
                match = re.search(r"frame=\s*(\d+)", line)
                if match:
                    now = time.perf_counter()
                    elapsed = now - start_time
                    avg_time_diff[i] = elapsed
                    estimated_total_time = self._average_list(avg_time_diff) * total_files
                    elapsed_total_time = now - start_time
                    percentage = (elapsed_total_time / estimated_total_time) * 100 if estimated_total_time else 0
                    i = (i + 1) % 10

                    progress_message = f"🟢 [~/{total_files}] Progress: {percentage:.2f}% elapsed."
                    output_text.delete(progress_line_index, f"{progress_line_index} lineend")
                    output_text.insert(progress_line_index, progress_message)
                    output_text.see("end")

            process.wait()
            self._current_process = None

            if self._cancel_requested:
                return

            if process.returncode == 0:
                output_text.insert("end", f"\n✅ Successfully joined videos into: {output_file}\n")
            else:
                output_text.insert("end", "\n❌ FFmpeg failed! Check the output above for details.\n")

            output_text.see("end")
            root.after(1000, lambda: (
                __import__('tkinter.messagebox').showinfo("Done", "✅ All videos have been joined!"),
                root.destroy()
            ))

        except FileNotFoundError:
            self._current_process = None
            __import__('tkinter.messagebox').showerror(
                "Error", "FFmpeg not found! Make sure it's installed and added to PATH."
            )
        except Exception as e:
            self._current_process = None
            output_text.insert("end", f"\n❌ Error: {str(e)}\n")
            output_text.see("end")
    
    def get_video_files(self, folder_path: str) -> List[str]:
        """Get list of video files from a folder.
        
        Args:
            folder_path: Path to folder containing videos
            
        Returns:
            Sorted list of video file paths
        """
        video_files = sorted([
            os.path.join(folder_path, f).replace("\\", "/")
            for f in os.listdir(folder_path)
            if f.lower().endswith(SUPPORTED_VIDEO_FORMATS)
        ])
        return video_files

