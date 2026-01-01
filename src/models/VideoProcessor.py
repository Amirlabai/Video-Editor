"""
VideoProcessor class for handling video encoding operations.
"""

import subprocess
import re
import time
import os
import logging
from typing import List, Tuple, Optional, Callable
from threading import Thread
from tkinter import messagebox

from .FFmpegCommandBuilder import FFmpegCommandBuilder
from .constants import (
    PROCESS_TERMINATION_TIMEOUT, CANCELLATION_MESSAGE_DELAY,
    HD_WIDTH, HD_HEIGHT, DEFAULT_CRF, DEFAULT_PRESET
)

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video encoding operations with progress tracking and error handling."""
    
    def __init__(self):
        """Initialize VideoProcessor."""
        self._current_process: Optional[subprocess.Popen] = None
        self._cancel_requested: bool = False
    
    def cancel(self) -> None:
        """Cancel the current processing operation."""
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
    
    def _process_ffmpeg_output(
        self,
        process: subprocess.Popen,
        output_text,
        progress_line_index: str,
        total_frames: Optional[int],
        error_list: List[str],
        input_file: str
    ) -> Tuple[int, List[str]]:
        """Process FFmpeg stdout output, track progress, and capture errors.
        
        Args:
            process: FFmpeg subprocess
            output_text: Tkinter Text widget for output
            progress_line_index: Index of progress line in output_text
            total_frames: Total number of frames (None if unknown)
            error_list: List to append errors to
            input_file: Input file path for logging
            
        Returns:
            Tuple of (return_code, error_list)
        """
        start_time = time.perf_counter()
        tot_time = start_time
        prev_frames = 0
        avg_frame_diff = [0] * 50
        avg_time_diff = [0] * 50
        avg_frame = 0
        avg_time = 0
        i = 0
        j = 0
        
        error_patterns = [
            r'\[error\]', r'Error', r'error', r'ERROR',
            r'Failed', r'failed', r'FAILED',
            r'Impossible', r'impossible',
            r'Could not', r'could not',
            r'Cannot', r'cannot',
            r'Invalid', r'invalid',
            r'not found', r'Not found', r'NOT FOUND',
            r'Permission denied', r'permission denied',
            r'No such file', r'no such file',
            r'Hardware is lacking', r'hardware is lacking',
            r'Function not implemented', r'function not implemented'
        ]

        for line in process.stdout:
            # Check for cancellation
            if self._cancel_requested:
                logger.info("Cancel requested, terminating FFmpeg process")
                process.terminate()
                try:
                    process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                output_text.insert("end", "\n⚠️ Operation cancelled by user\n")
                output_text.see("end")
                return -1, error_list
            
            # Check for error patterns
            for pattern in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    error_list.append(line.strip())
                    break
            
            # Track progress
            match = re.search(r"frame=\s*(\d+)", line)
            if match:
                frames = int(match.group(1))
                if total_frames:
                    frame_diff = frames - prev_frames
                    now = time.perf_counter()
                    elapsed = now - start_time
                    
                    avg_frame_diff[i] = frame_diff
                    avg_time_diff[i] = elapsed
                    if j == 0:
                        avg_frame = self._average_list(avg_frame_diff)
                        avg_time = self._average_list(avg_time_diff)
                        i = (i + 1) % 50

                    if avg_time > 0 and avg_frame > 0:
                        remaining_time = ((total_frames - frames) / (avg_frame / avg_time))
                    else:
                        remaining_time = 0
                    
                    remaining_time = int(remaining_time)
                    hours, minutes = divmod(remaining_time, 3600)
                    minutes, seconds = divmod(minutes, 60)
                    percent = (frames / total_frames) * 100
                    progress_message = (
                        f"🟢 Progress: {frames}/{total_frames} frames ({percent:.2f}%) "
                        f"avg frame: {avg_frame} | Running: {(now - tot_time)/60:.2f} - "
                        f"Remaining: {hours:02}:{minutes:02}:{seconds:02}"
                    )

                    output_text.delete(progress_line_index, f"{progress_line_index} lineend")
                    output_text.insert(progress_line_index, progress_message)
                    output_text.see("end")

                    prev_frames = frames
                    start_time = now
                    j = (j + 1) % 5

        return_code = process.wait()
        return return_code, error_list
    
    def scale_video_cpu(
        self,
        input_file: str,
        output_file: str,
        total_frames: Optional[int],
        output_text,
        root,
        ratio: bool = False,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET,
        threads: int = 0
    ) -> None:
        """Scale video using CPU encoding.
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            total_frames: Total number of frames (None if unknown)
            output_text: Tkinter Text widget for output
            root: Tkinter root window
            ratio: Whether to maintain aspect ratio
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor
            preset: Encoding preset
            threads: Number of threads (0 = auto)
        """
        self._cancel_requested = False
        
        # Build FFmpeg command
        ffmpeg_cmd = FFmpegCommandBuilder.build_scale_command_cpu(
            input_file, output_file, xaxis, yaxis, crf, preset, threads
        )
        
        error_list: List[str] = []
        
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

            threading_info = f" with {threads} threads" if threads > 0 else " (auto threading)"
            output_text.insert("end", f"🚀 Starting FFmpeg{threading_info}...\n")
            output_text.see("end")

            # Placeholder for progress line
            progress_line_index = output_text.index("end")
            output_text.insert("end", f"🟢 {input_file} Starting...\n")
            output_text.see("end")

            # Process FFmpeg output and track progress
            return_code, error_list = self._process_ffmpeg_output(
                process, output_text, progress_line_index, total_frames, error_list, input_file
            )
            
            # Clear process reference
            self._current_process = None
            
            # Handle cancellation
            if self._cancel_requested or return_code == -1:
                # Clean up partial output file
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        logger.info(f"Removed partial output file: {output_file}")
                        output_text.insert("end", f"\n🗑️ Partial output file removed.\n")
                    except Exception as e:
                        logger.warning(f"Could not remove partial file: {e}")
                output_text.insert("end", f"\n⚠️ Operation cancelled by user.\n")
                output_text.see("end")
                # Close window after showing cancellation message
                root.after(CANCELLATION_MESSAGE_DELAY, lambda: (
                    messagebox.showinfo("Cancelled", "Operation was cancelled."),
                    root.destroy()
                ))
                return
            
            # Handle errors and success
            self._handle_process_result(process, return_code, error_list, output_file, output_text, root)
            
        except FileNotFoundError:
            self._current_process = None
            messagebox.showerror(
                "Error", "FFmpeg not found! Make sure it's installed and added to PATH."
            )
        except Exception as e:
            self._current_process = None
            logger.error(f"Error during CPU encoding: {e}")
            output_text.insert("end", f"\n❌ Error: {str(e)}\n")
            output_text.see("end")
    
    def scale_video_gpu(
        self,
        input_file: str,
        output_file: str,
        total_frames: Optional[int],
        output_text,
        root,
        ratio: bool = False,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET
    ) -> None:
        """Scale video using GPU encoding (NVENC).
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            total_frames: Total number of frames (None if unknown)
            output_text: Tkinter Text widget for output
            root: Tkinter root window
            ratio: Whether to maintain aspect ratio
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor
            preset: Encoding preset
        """
        self._cancel_requested = False
        
        # Build FFmpeg command
        ffmpeg_cmd = FFmpegCommandBuilder.build_scale_command_gpu(
            input_file, output_file, xaxis, yaxis, crf, preset
        )
        
        error_list: List[str] = []
        
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

            output_text.insert("end", "🚀 Starting FFmpeg with GPU acceleration (NVENC)...\n")
            output_text.see("end")

            # Placeholder for progress line
            progress_line_index = output_text.index("end")
            output_text.insert("end", f"🟢 {input_file} Starting...\n")
            output_text.see("end")

            # Process FFmpeg output and track progress
            return_code, error_list = self._process_ffmpeg_output(
                process, output_text, progress_line_index, total_frames, error_list, input_file
            )
            
            # Clear process reference
            self._current_process = None
            
            # Handle cancellation
            if self._cancel_requested or return_code == -1:
                # Clean up partial output file
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        logger.info(f"Removed partial output file: {output_file}")
                        output_text.insert("end", f"\n🗑️ Partial output file removed.\n")
                    except Exception as e:
                        logger.warning(f"Could not remove partial file: {e}")
                output_text.insert("end", f"\n⚠️ Operation cancelled by user.\n")
                output_text.see("end")
                # Close window after showing cancellation message
                root.after(CANCELLATION_MESSAGE_DELAY, lambda: (
                    messagebox.showinfo("Cancelled", "Operation was cancelled."),
                    root.destroy()
                ))
                return
            
            # Check for NVENC DLL loading errors specifically
            nvenc_dll_error = any(
                "Cannot load nvEncodeAPI64.dll" in err or "nvEncodeAPI" in err
                for err in error_list
            )
            
            # Handle errors and success
            if nvenc_dll_error:
                # GPU error - fallback to CPU
                logger.warning("NVENC DLL error detected, falling back to CPU encoding")
                output_text.insert("end", "\n⚠️ GPU encoding failed, falling back to CPU...\n")
                output_text.see("end")
                # Remove failed GPU output and retry with CPU
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except Exception:
                        pass
                self.scale_video_cpu(
                    input_file, output_file, total_frames, output_text, root,
                    ratio, xaxis, yaxis, crf, preset, threads=0
                )
            else:
                self._handle_process_result(process, return_code, error_list, output_file, output_text, root)
            
        except FileNotFoundError:
            self._current_process = None
            messagebox.showerror(
                "Error", "FFmpeg not found! Make sure it's installed and added to PATH."
            )
        except Exception as e:
            self._current_process = None
            logger.error(f"Error during GPU encoding: {e}")
            output_text.insert("end", f"\n❌ Error: {str(e)}\n")
            output_text.see("end")
    
    def _handle_process_result(
        self,
        process: subprocess.Popen,
        return_code: int,
        error_list: List[str],
        output_file: str,
        output_text,
        root
    ) -> None:
        """Handle the result of a video processing operation.
        
        Args:
            process: FFmpeg subprocess
            return_code: Process return code
            error_list: List of captured errors
            output_file: Output file path
            output_text: Tkinter Text widget
            root: Tkinter root window
        """
        from tkinter import messagebox
        from .constants import SUCCESS_MESSAGE_DELAY
        
        if return_code == 0:
            output_text.insert("end", f"\n✅ Successfully processed: {output_file}\n")
            if error_list:
                output_text.insert("end", f"\n⚠️ Warnings detected: {len(error_list)} warning(s)\n")
                for error in error_list[:5]:  # Show first 5 errors
                    output_text.insert("end", f"  - {error}\n")
                if len(error_list) > 5:
                    output_text.insert("end", f"  ... and {len(error_list) - 5} more\n")
        else:
            error_msg = self._get_ffmpeg_error_code(return_code)
            output_text.insert("end", f"\n❌ FFmpeg failed with return code {return_code}: {error_msg}\n")
            if error_list:
                output_text.insert("end", "\nErrors detected:\n")
                for error in error_list:
                    output_text.insert("end", f"  - {error}\n")
        
        output_text.see("end")
        root.after(SUCCESS_MESSAGE_DELAY, lambda: (
            messagebox.showinfo("Done", "✅ Video processing completed!"),
            root.destroy()
        ))
    
    @staticmethod
    def _get_ffmpeg_error_code(return_code: int) -> str:
        """Look up FFmpeg return code meanings."""
        error_codes = {
            0: "Success",
            1: "Unknown error",
            -1: "Process terminated",
            -2: "Invalid argument",
            -3: "No such file or directory",
            -4: "Permission denied",
            -5: "I/O error",
            -6: "No space left on device",
            -7: "Out of memory",
            -8: "Invalid data found",
            -9: "Operation not permitted",
            -10: "Protocol error",
            -11: "Not found",
            -12: "Not available",
            -13: "Invalid",
            -14: "EOF",
            -15: "Not implemented",
            -16: "Bug",
            -17: "Unknown error",
            -18: "Experimental",
            -19: "Input changed",
            -20: "Output changed",
            -22: "Invalid argument",
            -40: "Function not implemented",
            -50: "Invalid argument",
            -100: "Unknown error"
        }
        return error_codes.get(return_code, f"Unknown error code: {return_code}")

