"""
BatchProcessor class for processing multiple videos in a folder.
"""

import os
from datetime import datetime
from typing import Optional, List, Callable
import logging
from threading import Thread
from tkinter import messagebox

from .VideoInfo import VideoInfo
from .VideoProcessor import VideoProcessor
from .constants import SUPPORTED_VIDEO_FORMATS

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Handles batch processing of multiple video files."""
    
    def __init__(self):
        """Initialize BatchProcessor."""
        self.processor = VideoProcessor()
        self._cancel_requested: bool = False
    
    def cancel(self) -> None:
        """Cancel the current batch processing operation."""
        self._cancel_requested = True
        self.processor.cancel()
    
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
    
    def process_videos_in_folder(
        self,
        folder_path: str,
        progress_labels: Optional[dict],
        status_text,
        root,
        use_gpu: bool = False,
        threads: int = 0,
        output_folder: Optional[str] = None,
        is_vertical: bool = False,
        xaxis: str = None,
        yaxis: str = None,
        crf: str = None,
        preset: str = None,
        fps: Optional[float] = None
    ) -> None:
        """Process all videos in a folder.
        
        Args:
            folder_path: Path to folder containing videos
            progress_labels: Dictionary of Tkinter Label widgets for progress updates
            status_text: Tkinter Text widget for status/error messages
            root: Tkinter root window
            use_gpu: Whether to use GPU encoding
            threads: Number of threads (0 = auto)
            output_folder: Output folder path (None = same as input)
            is_vertical: Whether orientation is vertical
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor
            preset: Encoding preset
        """
        self._cancel_requested = False
        video_files = self.get_video_files(folder_path)
        total_files = len(video_files)
        
        if total_files == 0:
            root.after(0, lambda st=status_text: (st.insert("end", "No video files found in the selected folder.\n"), st.see("end")) if st.winfo_exists() else None)
            return
        
        # Update progress labels with initial values (thread-safe)
        if progress_labels:
            def update_labels():
                if "Files Processed:" in progress_labels:
                    progress_labels["Files Processed:"].config(text=f"0/{total_files}")
                if "Overall Progress:" in progress_labels:
                    progress_labels["Overall Progress:"].config(text="0.00%")
            root.after(0, update_labels)
        
        # Set defaults if not provided
        if not xaxis or not yaxis:
            from .constants import HD_WIDTH, HD_HEIGHT
            xaxis = str(HD_WIDTH)
            yaxis = str(HD_HEIGHT)
        
        if not crf:
            from .constants import DEFAULT_CRF
            crf = DEFAULT_CRF
        
        if not preset:
            from .constants import DEFAULT_PRESET
            preset = DEFAULT_PRESET
        
        # Process each file
        for index, video_file in enumerate(video_files, 1):
            # Check for cancellation
            if self._cancel_requested:
                root.after(0, lambda st=status_text: (st.insert("end", "\nBatch processing cancelled by user.\n"), st.see("end")) if st.winfo_exists() else None)
                return
            
            filename = os.path.basename(video_file)
            
            # Update batch-level progress labels (thread-safe)
            if progress_labels:
                def update_batch_progress(idx=index, name=filename):
                    try:
                        if "Files Processed:" in progress_labels:
                            progress_labels["Files Processed:"].config(text=f"{idx}/{total_files}")
                        if "Current File:" in progress_labels:
                            progress_labels["Current File:"].config(text=name)
                        if "Overall Progress:" in progress_labels:
                            percent = (idx / total_files) * 100
                            progress_labels["Overall Progress:"].config(text=f"{percent:.2f}%")
                        # Reset per-file progress labels for new file
                        if "Frames Processed:" in progress_labels:
                            progress_labels["Frames Processed:"].config(text="0")
                        if "Progress:" in progress_labels:
                            progress_labels["Progress:"].config(text="0.00%")
                        if "Average Frame Rate:" in progress_labels:
                            progress_labels["Average Frame Rate:"].config(text="0")
                        if "Time Running:" in progress_labels:
                            progress_labels["Time Running:"].config(text="0.00 min")
                        if "Time Remaining:" in progress_labels:
                            progress_labels["Time Remaining:"].config(text="00:00:00")
                    except:
                        pass  # Widget may have been destroyed
                root.after(0, update_batch_progress)
            
            self._process_single_file(
                folder_path, status_text, root, index, filename, total_files,
                is_vertical, use_gpu, threads, output_folder, xaxis, yaxis, crf, preset, fps,
                progress_labels
            )
        
        # Show completion message
        if not self._cancel_requested:
            root.after(0, lambda st=status_text: (st.insert("end", "\nAll videos have been processed successfully!\n"), st.see("end")) if st.winfo_exists() else None)
            root.after(1000, lambda: (
                messagebox.showinfo("Done", "All videos have been processed!"),
                root.destroy()
            ))
    
    def _process_single_file(
        self,
        folder_path: str,
        status_text,
        root,
        index: int,
        filename: str,
        total_files: int,
        is_vertical: bool,
        use_gpu: bool,
        threads: int,
        output_folder: Optional[str],
        xaxis: str,
        yaxis: str,
        crf: str,
        preset: str,
        fps: Optional[float] = None,
        progress_labels: Optional[dict] = None
    ) -> None:
        """Process a single video file.
        
        Args:
            folder_path: Input folder path
            status_text: Tkinter Text widget for status messages
            root: Tkinter root window
            index: Current file index
            filename: Video filename
            total_files: Total number of files
            is_vertical: Whether orientation is vertical
            use_gpu: Whether to use GPU
            threads: Number of threads
            output_folder: Output folder path
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor
            preset: Encoding preset
        """
        now = datetime.now()
        input_file = os.path.join(folder_path, filename)
        
        # Determine output filename
        if "mp4" in filename:
            file_name = filename.split(".")[0]
        else:
            file_name = filename
        
        # Determine output path
        orientation = "_vertical" if is_vertical else "_horizontal"
        if output_folder:
            output_file = os.path.join(
                output_folder,
                f"{file_name}_{orientation}_{crf}_{preset}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            )
        else:
            output_file = os.path.join(
                folder_path,
                f"{file_name}_{orientation}_{crf}_{preset}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            )
        
        # Create VideoInfo instance for this file and get total frames
        video_info = VideoInfo(input_file)
        total_frames = video_info.get_total_frames()
        
        # Get input file size
        input_size = None
        if os.path.exists(input_file):
            try:
                input_size = os.path.getsize(input_file)
            except Exception:
                pass
        
        # Display file info in status text (thread-safe)
        def update_status():
            try:
                if not status_text.winfo_exists():
                    return
                if total_frames:
                    status_text.insert("end", f"\nProcessing file {index}/{total_files}: {filename}\n")
                    if input_size is not None:
                        from .VideoProcessor import VideoProcessor
                        status_text.insert("end", f"Input size: {VideoProcessor.format_file_size(input_size)}\n")
                    status_text.insert("end", f"Output: {os.path.basename(output_file)}\n")
                    status_text.insert("end", f"Frames: {total_frames}\n")
                else:
                    status_text.insert("end", f"\nProcessing file {index}/{total_files}: {filename} (frame count error)\n")
                    if input_size is not None:
                        from .VideoProcessor import VideoProcessor
                        status_text.insert("end", f"Input size: {VideoProcessor.format_file_size(input_size)}\n")
                    status_text.insert("end", f"Output: {os.path.basename(output_file)}\n")
                status_text.see("end")
            except:
                pass  # Widget may have been destroyed
        root.after(0, update_status)
        
        # Process video (pass progress_labels to show per-file progress)
        if use_gpu:
            self.processor.scale_video_gpu(
                input_file, output_file, total_frames, progress_labels, status_text, root,
                is_vertical, xaxis, yaxis, crf, preset, fps, close_window=False
            )
        else:
            self.processor.scale_video_cpu(
                input_file, output_file, total_frames, progress_labels, status_text, root,
                is_vertical, xaxis, yaxis, crf, preset, threads, fps, close_window=False
            )
        
        root.after(0, lambda st=status_text: st.insert("end", "\n") if st.winfo_exists() else None)
    
    def _extract_ratio_from_filename(self, filename: str) -> tuple:
        """Extract ratio information from filename if available.
        
        Args:
            filename: Video filename
            
        Returns:
            Ratio tuple (orientation, ratio_name, x, y, crf, preset)
        """
        # Default values
        from .constants import HD_WIDTH, HD_HEIGHT, DEFAULT_CRF, DEFAULT_PRESET
        
        # Try to extract from filename (format: name_ratio_crf_preset_timestamp.mp4)
        parts = filename.split('_')
        if len(parts) >= 4:
            try:
                ratio_name = parts[-4] if len(parts) >= 4 else "HD"
                crf = parts[-3] if len(parts) >= 3 else DEFAULT_CRF
                preset = parts[-2] if len(parts) >= 2 else DEFAULT_PRESET
                
                # Map ratio names to dimensions
                ratio_map = {
                    "HD": (HD_WIDTH, HD_HEIGHT),
                    "FHD": (1920, 1080),
                    "4K": (3840, 2160)
                }
                
                x, y = ratio_map.get(ratio_name, (HD_WIDTH, HD_HEIGHT))
                return (False, ratio_name, str(x), str(y), crf, preset)
            except (ValueError, IndexError):
                pass
        
        # Default return
        return (False, "HD", str(HD_WIDTH), str(HD_HEIGHT), DEFAULT_CRF, DEFAULT_PRESET)

