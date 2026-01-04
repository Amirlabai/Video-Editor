"""
VideoProcessor class for handling video encoding operations.
"""

import subprocess
import re
import time
import os
import logging
import tkinter as tk
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
        progress_labels: Optional[dict],
        status_text,
        total_frames: Optional[int],
        error_list: List[str],
        input_file: str,
        root=None,
        target_fps: Optional[float] = None,
        input_duration: Optional[float] = None
    ) -> Tuple[int, List[str]]:
        """Process FFmpeg stdout output, track progress, and capture errors.
        
        Uses FFmpeg's structured progress output for accurate tracking, especially
        when FPS changes affect the total output frame count.
        
        Args:
            process: FFmpeg subprocess
            progress_labels: Dictionary of Tkinter Label widgets for progress updates (or None for text widget mode)
            status_text: Tkinter Text widget for status/error messages
            total_frames: Total number of frames from input (used as fallback if output frames unknown)
            error_list: List to append errors to
            input_file: Input file path for logging
            root: Tkinter root window
            target_fps: Target FPS for output (None to keep current)
            input_duration: Input video duration in seconds (for calculating output frames when FPS changes)
            
        Returns:
            Tuple of (return_code, error_list)
        """
        start_time = time.perf_counter()
        tot_time = start_time
        
        # Progress tracking state
        current_frame = 0
        encoding_fps = 0.0  # FFmpeg's encoding speed (frames/second)
        output_duration = None  # Calculated output duration from FFmpeg
        
        # Calculate expected output frames if FPS is being changed
        output_total_frames = total_frames  # Default to input frames
        if target_fps is not None and input_duration is not None:
            # When FPS changes, output will have different frame count
            output_total_frames = int(input_duration * target_fps)
        elif target_fps is not None and total_frames is not None:
            # Fallback: estimate from input frames and FPS ratio
            # This is less accurate but better than nothing
            if hasattr(self, '_input_fps') and self._input_fps and self._input_fps > 0:
                fps_ratio = target_fps / self._input_fps
                output_total_frames = int(total_frames * fps_ratio)
        
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

        # Parse FFmpeg's structured progress output
        progress_data = {}
        for line in process.stdout:
            # Check for cancellation
            if self._cancel_requested:
                logger.info("Cancel requested, terminating FFmpeg process")
                process.terminate()
                try:
                    process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                # Thread-safe widget update
                if status_text and root:
                    try:
                        root.after(0, lambda st=status_text: (st.insert("end", "\nOperation cancelled by user\n"), st.see("end")) if st.winfo_exists() else None)
                    except:
                        pass  # Widget may have been destroyed
                return -1, error_list
            
            # Check for error patterns (in stderr lines that may be mixed in)
            for pattern in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    error_list.append(line.strip())
                    break
            
            # Parse FFmpeg progress output (key=value format)
            # Progress output is separated by newlines, each line is key=value
            line = line.strip()
            if '=' in line and not line.startswith('ffmpeg') and not line.startswith('Input'):
                try:
                    key, value = line.split('=', 1)
                    progress_data[key] = value
                except ValueError:
                    pass
            
            # Check if we have a complete progress update (when we see 'progress=continue' or 'progress=end')
            if 'progress' in progress_data:
                now = time.perf_counter()
                
                # Extract progress information
                if 'frame' in progress_data:
                    try:
                        current_frame = int(progress_data['frame'])
                    except (ValueError, TypeError):
                        pass
                
                if 'fps' in progress_data:
                    try:
                        encoding_fps = float(progress_data['fps'])
                    except (ValueError, TypeError):
                        pass
                
                if 'out_time_ms' in progress_data:
                    try:
                        output_time_ms = int(progress_data['out_time_ms'])
                        output_duration = output_time_ms / 1000000.0  # Convert to seconds
                    except (ValueError, TypeError):
                        pass
                
                # Calculate progress percentage
                # Prefer frame-based if we have output_total_frames, otherwise use time-based
                if output_total_frames and output_total_frames > 0:
                    percent = min(100.0, (current_frame / output_total_frames) * 100)
                elif output_duration and input_duration and input_duration > 0:
                    # Fallback to time-based progress
                    percent = min(100.0, (output_duration / input_duration) * 100)
                else:
                    percent = 0.0
                
                # Calculate remaining time
                if encoding_fps > 0 and output_total_frames and output_total_frames > 0:
                    remaining_frames = max(0, output_total_frames - current_frame)
                    remaining_time = remaining_frames / encoding_fps
                elif output_duration is not None and input_duration and input_duration > 0:
                    # Fallback to time-based estimation
                    remaining_time = max(0, input_duration - output_duration)
                else:
                    remaining_time = 0
                
                remaining_time = int(remaining_time)
                hours, minutes = divmod(remaining_time, 3600)
                minutes, seconds = divmod(minutes, 60)
                
                # Update progress labels if available (thread-safe)
                if progress_labels and root:
                    def update_progress(
                        f=current_frame, 
                        tf=output_total_frames or total_frames or 0, 
                        p=percent, 
                        cf=encoding_fps, 
                        tr=(now - tot_time)/60, 
                        rem=f"{hours:02}:{minutes:02}:{seconds:02}"
                    ):
                        try:
                            if "Frames Processed:" in progress_labels:
                                progress_labels["Frames Processed:"].config(text=f"{f}/{tf}")
                            if "Progress:" in progress_labels:
                                progress_labels["Progress:"].config(text=f"{p:.2f}%")
                            if "Average Frame Rate:" in progress_labels:
                                progress_labels["Average Frame Rate:"].config(text=f"{cf:.1f} fps")
                            if "Time Running:" in progress_labels:
                                progress_labels["Time Running:"].config(text=f"{tr:.2f} min")
                            if "Time Remaining:" in progress_labels:
                                progress_labels["Time Remaining:"].config(text=rem)
                        except:
                            pass  # Widget may have been destroyed
                    root.after(0, update_progress)
                
                # Reset progress_data for next update block
                if progress_data.get('progress') == 'end':
                    break
                # Clear progress_data after processing - next block will have all data
                progress_data = {}

        return_code = process.wait()
        return return_code, error_list
    
    def scale_video_cpu(
        self,
        input_file: str,
        output_file: str,
        total_frames: Optional[int],
        progress_labels: Optional[dict],
        status_text,
        root,
        ratio: bool = False,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET,
        threads: int = 0,
        fps: Optional[float] = None,
        close_window: bool = True
    ) -> None:
        """Scale video using CPU encoding.
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            total_frames: Total number of frames (None if unknown)
            progress_labels: Dictionary of Tkinter Label widgets for progress updates (or None for text widget mode)
            status_text: Tkinter Text widget for status/error messages
            root: Tkinter root window
            ratio: Whether to maintain aspect ratio
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor
            preset: Encoding preset
            threads: Number of threads (0 = auto)
            fps: Target FPS (None to keep current)
        """
        self._cancel_requested = False
        
        # Get input duration for accurate progress tracking when FPS changes
        from .VideoInfo import VideoInfo
        video_info = VideoInfo(input_file)
        input_duration = video_info.get_duration()
        input_fps = video_info.fps
        if input_fps:
            self._input_fps = input_fps
        
        # Build FFmpeg command
        ffmpeg_cmd = FFmpegCommandBuilder.build_scale_command_cpu(
            input_file, output_file, xaxis, yaxis, crf, preset, threads, fps=fps
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
            root.after(0, lambda st=status_text, info=threading_info: (st.insert("end", f"Starting FFmpeg{info}...\n"), st.see("end")) if st.winfo_exists() else None)

            # Process FFmpeg output and track progress
            return_code, error_list = self._process_ffmpeg_output(
                process, progress_labels, status_text, total_frames, error_list, input_file, root,
                target_fps=fps, input_duration=input_duration
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
                        root.after(0, lambda st=status_text: st.insert("end", f"\nPartial output file removed.\n") if st.winfo_exists() else None)
                    except Exception as e:
                        logger.warning(f"Could not remove partial file: {e}")
                root.after(0, lambda st=status_text: (st.insert("end", f"\nOperation cancelled by user.\n"), st.see("end")) if st.winfo_exists() else None)
                # Close window after showing cancellation message
                root.after(CANCELLATION_MESSAGE_DELAY, lambda: (
                    messagebox.showinfo("Cancelled", "Operation was cancelled."),
                    root.destroy()
                ))
                return
            
            # Handle errors and success
            self._handle_process_result(process, return_code, error_list, output_file, status_text, root, input_file, close_window)
            
        except FileNotFoundError:
            self._current_process = None
            messagebox.showerror(
                "Error", "FFmpeg not found! Make sure it's installed and added to PATH."
            )
        except Exception as e:
            self._current_process = None
            logger.error(f"Error during CPU encoding: {e}")
            error_msg = str(e)  # Capture error message for lambda
            root.after(0, lambda msg=error_msg: (status_text.insert("end", f"\nError: {msg}\n"), status_text.see("end")) if status_text.winfo_exists() else None)
    
    def scale_video_gpu(
        self,
        input_file: str,
        output_file: str,
        total_frames: Optional[int],
        progress_labels: Optional[dict],
        status_text,
        root,
        ratio: bool = False,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET,
        fps: Optional[float] = None,
        close_window: bool = True
    ) -> None:
        """Scale video using GPU encoding (NVENC).
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            total_frames: Total number of frames (None if unknown)
            progress_labels: Dictionary of Tkinter Label widgets for progress updates (or None for text widget mode)
            status_text: Tkinter Text widget for status/error messages
            root: Tkinter root window
            ratio: Whether to maintain aspect ratio
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor
            preset: Encoding preset
            fps: Target FPS (None to keep current)
        """
        self._cancel_requested = False
        
        # Get input duration for accurate progress tracking when FPS changes
        from .VideoInfo import VideoInfo
        video_info = VideoInfo(input_file)
        input_duration = video_info.get_duration()
        input_fps = video_info.fps
        if input_fps:
            self._input_fps = input_fps
        
        # Build FFmpeg command
        ffmpeg_cmd = FFmpegCommandBuilder.build_scale_command_gpu(
            input_file, output_file, xaxis, yaxis, crf, preset, fps=fps
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

            root.after(0, lambda st=status_text: (st.insert("end", "Starting FFmpeg with GPU acceleration (NVENC)...\n"), st.see("end")) if st.winfo_exists() else None)

            # Process FFmpeg output and track progress
            return_code, error_list = self._process_ffmpeg_output(
                process, progress_labels, status_text, total_frames, error_list, input_file, root,
                target_fps=fps, input_duration=input_duration
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
                        root.after(0, lambda st=status_text: st.insert("end", f"\nPartial output file removed.\n") if st.winfo_exists() else None)
                    except Exception as e:
                        logger.warning(f"Could not remove partial file: {e}")
                root.after(0, lambda st=status_text: (st.insert("end", f"\nOperation cancelled by user.\n"), st.see("end")) if st.winfo_exists() else None)
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
                root.after(0, lambda st=status_text: (st.insert("end", "\nGPU encoding failed, falling back to CPU...\n"), st.see("end")) if st.winfo_exists() else None)
                # Remove failed GPU output and retry with CPU
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except Exception:
                        pass
                self.scale_video_cpu(
                    input_file, output_file, total_frames, progress_labels, status_text, root,
                    ratio, xaxis, yaxis, crf, preset, threads=0, close_window=close_window
                )
            else:
                self._handle_process_result(process, return_code, error_list, output_file, status_text, root, input_file, close_window)
            
        except FileNotFoundError:
            self._current_process = None
            messagebox.showerror(
                "Error", "FFmpeg not found! Make sure it's installed and added to PATH."
            )
        except Exception as e:
            self._current_process = None
            logger.error(f"Error during GPU encoding: {e}")
            error_msg = str(e)  # Capture error message for lambda
            root.after(0, lambda st=status_text, msg=error_msg: (st.insert("end", f"\nError: {msg}\n"), st.see("end")) if st.winfo_exists() else None)
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in bytes to human-readable format.
        
        Args:
            size_bytes: File size in bytes
            
        Returns:
            Formatted string (e.g., "1.5 MB", "500 KB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def _handle_process_result(
        self,
        process: subprocess.Popen,
        return_code: int,
        error_list: List[str],
        output_file: str,
        output_text,
        root,
        input_file: Optional[str] = None,
        close_window: bool = True
    ) -> None:
        """Handle the result of a video processing operation.
        
        Args:
            process: FFmpeg subprocess
            return_code: Process return code
            error_list: List of captured errors
            output_file: Output file path
            output_text: Tkinter Text widget
            root: Tkinter root window
            input_file: Input file path (optional, for size comparison)
        """
        from tkinter import messagebox
        from .constants import SUCCESS_MESSAGE_DELAY
        
        if return_code == 0:
            output_text.insert("end", f"\nSuccessfully processed: {output_file}\n")
            
            # Show file size comparison if input file is provided
            if input_file and os.path.exists(input_file) and os.path.exists(output_file):
                try:
                    input_size = os.path.getsize(input_file)
                    output_size = os.path.getsize(output_file)
                    size_reduction = input_size - output_size
                    reduction_percent = (size_reduction / input_size * 100) if input_size > 0 else 0
                    
                    output_text.insert("end", f"\nFile Size Comparison:\n")
                    output_text.insert("end", f"  Input:  {VideoProcessor.format_file_size(input_size)}\n")
                    output_text.insert("end", f"  Output: {VideoProcessor.format_file_size(output_size)}\n")
                    if reduction_percent > 0:
                        output_text.insert("end", f"  Reduction: {VideoProcessor.format_file_size(size_reduction)} ({reduction_percent:.1f}% smaller)\n")
                    elif reduction_percent < 0:
                        output_text.insert("end", f"  Increase: {VideoProcessor.format_file_size(abs(size_reduction))} ({abs(reduction_percent):.1f}% larger)\n")
                    else:
                        output_text.insert("end", f"  No size change\n")
                except Exception as e:
                    logger.warning(f"Could not get file sizes: {e}")
            
            if error_list:
                output_text.insert("end", f"\nWarnings detected: {len(error_list)} warning(s)\n")
                for error in error_list[:5]:  # Show first 5 errors
                    output_text.insert("end", f"  - {error}\n")
                if len(error_list) > 5:
                    output_text.insert("end", f"  ... and {len(error_list) - 5} more\n")
        else:
            error_msg = self._get_ffmpeg_error_code(return_code)
            output_text.insert("end", f"\nFFmpeg failed with return code {return_code}: {error_msg}\n")
            if error_list:
                output_text.insert("end", "\nErrors detected:\n")
                for error in error_list:
                    output_text.insert("end", f"  - {error}\n")
        
        output_text.see("end")
        if close_window:
            root.after(SUCCESS_MESSAGE_DELAY, lambda: (
                messagebox.showinfo("Done", "Video processing completed!"),
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

