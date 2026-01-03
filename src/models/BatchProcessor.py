"""
BatchProcessor class for processing multiple videos in a folder.
"""

import os
from datetime import datetime
from typing import Optional, List
import logging
from threading import Thread

from .VideoInfo import VideoInfo
from .VideoProcessor import VideoProcessor
from .constants import SUPPORTED_VIDEO_FORMATS

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Handles batch processing of multiple video files."""
    
    def __init__(self):
        """Initialize BatchProcessor."""
        self.processor = VideoProcessor()
        self.video_info = VideoInfo()
    
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
        output_text,
        root,
        use_gpu: bool = False,
        threads: int = 0,
        output_folder: Optional[str] = None,
        ratio: tuple = None,
        xaxis: str = None,
        yaxis: str = None,
        crf: str = None,
        preset: str = None,
        fps: Optional[float] = None
    ) -> None:
        """Process all videos in a folder.
        
        Args:
            folder_path: Path to folder containing videos
            output_text: Tkinter Text widget for output
            root: Tkinter root window
            use_gpu: Whether to use GPU encoding
            threads: Number of threads (0 = auto)
            output_folder: Output folder path (None = same as input)
            ratio: Video orientation ratio tuple
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor
            preset: Encoding preset
        """
        video_files = self.get_video_files(folder_path)
        total_files = len(video_files)
        
        if total_files == 0:
            output_text.insert("end", "No video files found in the selected folder.\n")
            output_text.see("end")
            return
        
        output_text.insert("end", f"\nFound {total_files} video files to process.\n")
        output_text.see("end")
        
        # Get video properties from first file
        if not ratio:
            ratio = self._extract_ratio_from_filename(video_files[0])
        
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
            filename = os.path.basename(video_file)
            self._process_single_file(
                folder_path, output_text, root, index, filename, total_files,
                ratio, use_gpu, threads, output_folder, xaxis, yaxis, crf, preset, fps
            )
        
        # Show completion message
        root.after(1000, lambda: (
                __import__('tkinter.messagebox').showinfo("Done", "All videos have been processed!"),
            root.destroy()
        ))
    
    def _process_single_file(
        self,
        folder_path: str,
        output_text,
        root,
        index: int,
        filename: str,
        total_files: int,
        ratio: tuple,
        use_gpu: bool,
        threads: int,
        output_folder: Optional[str],
        xaxis: str,
        yaxis: str,
        crf: str,
        preset: str,
        fps: Optional[float] = None
    ) -> None:
        """Process a single video file.
        
        Args:
            folder_path: Input folder path
            output_text: Tkinter Text widget
            root: Tkinter root window
            index: Current file index
            filename: Video filename
            total_files: Total number of files
            ratio: Video orientation ratio
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
        if output_folder:
            output_file = os.path.join(
                output_folder,
                f"{file_name}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            )
        else:
            output_file = os.path.join(
                folder_path,
                f"{file_name}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            )
        
        # Get total frames
        total_frames = self.video_info.get_total_frames(input_file)
        
        # Get input file size
        input_size = None
        if os.path.exists(input_file):
            try:
                input_size = os.path.getsize(input_file)
            except Exception:
                pass
        
        # Display file info
        if total_frames:
            output_text.insert("end", f"\nProcessing file {index}/{total_files}: {filename}\n")
            if input_size is not None:
                from .VideoProcessor import VideoProcessor
                output_text.insert("end", f"Input size: {VideoProcessor.format_file_size(input_size)}\n")
            output_text.insert("end", f"Output: {output_file}\n")
            output_text.insert("end", f"Frames: {total_frames}\n")
        else:
            output_text.insert("end", f"\nRunning {filename} (frame count error)\n")
            output_text.insert("end", f"\nProcessing file {index}/{total_files}: {filename}\n")
            if input_size is not None:
                from .VideoProcessor import VideoProcessor
                output_text.insert("end", f"Input size: {VideoProcessor.format_file_size(input_size)}\n")
            output_text.insert("end", f"Output: {output_file}\n")
        
        output_text.see("end")
        
        # Process video
        if use_gpu:
            self.processor.scale_video_gpu(
                input_file, output_file, total_frames, output_text, root,
                ratio[0], xaxis, yaxis, crf, preset, fps
            )
        else:
            self.processor.scale_video_cpu(
                input_file, output_file, total_frames, output_text, root,
                ratio[0], xaxis, yaxis, crf, preset, threads, fps
            )
        
        output_text.insert("end", "\n")
    
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

