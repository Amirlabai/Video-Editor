"""
VideoInfo class for extracting video metadata using ffprobe.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class VideoInfo:
    """Handles video metadata extraction and information retrieval."""
    
    @staticmethod
    def get_total_frames(video_path: str) -> Optional[int]:
        """Extract video duration and FPS using ffprobe to calculate total frames.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Total number of frames, or None if extraction fails
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration:stream=r_frame_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output_lines = result.stdout.strip().splitlines()
            if len(output_lines) > 2:
                duration_str = output_lines[-1]
            else:
                duration_str = output_lines[1]
            fps_str = output_lines[0].split("/")[0]
            if int(fps_str) == 0:
                fps_str = output_lines[1].split("/")[0]
            return int(int(float(duration_str)) * int(fps_str))
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError) as e:
            logger.error(f"Error getting total frames for {video_path}: {e}")
            return None
    
    @staticmethod
    def get_video_info(video_path: str) -> Optional[Tuple[str, int, int, str]]:
        """Extract codec, resolution, and framerate using ffprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Tuple of (codec, width, height, framerate) or None if extraction fails
        """
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,width,height,r_frame_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            codec, width, height, framerate = result.stdout.strip().splitlines()
            return codec, int(width), int(height), framerate
        except Exception as e:
            logger.error(f"Error getting video info for {video_path}: {e}")
            return None
    
    @staticmethod
    def get_fps_and_size(video_path: str) -> Optional[Tuple[float, int, int]]:
        """Extract FPS and video dimensions using ffprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Tuple of (fps, width, height) or None if extraction fails
        """
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().splitlines()
            width = int(lines[0])
            height = int(lines[1])
            framerate_str = lines[2]
            
            # Parse framerate (e.g., "30/1" or "29.97/1")
            if "/" in framerate_str:
                num, den = framerate_str.split("/")
                fps = float(num) / float(den)
            else:
                fps = float(framerate_str)
            
            return fps, width, height
        except Exception as e:
            logger.error(f"Error getting FPS and size for {video_path}: {e}")
            return None
    
    @staticmethod
    def check_compatibility(video_files: list) -> bool:
        """Check if all videos have matching codec, resolution, and framerate.
        
        Args:
            video_files: List of video file paths
            
        Returns:
            True if all videos are compatible, False otherwise
        """
        if not video_files:
            return False
        
        reference_info = VideoInfo.get_video_info(video_files[0])
        if not reference_info:
            return False

        for video in video_files[1:]:
            info = VideoInfo.get_video_info(video)
            if info != reference_info:
                return False

        return True
    
    @staticmethod
    def sanitize_path(file_path: str) -> Optional[str]:
        """Sanitize file path to prevent path injection attacks.
        
        Args:
            file_path: Input file path
            
        Returns:
            Sanitized absolute path, or None if invalid
        """
        try:
            # Convert to Path object and resolve to absolute path
            path = Path(file_path).resolve()
            
            # Check if path exists and is a file
            if not path.exists():
                logger.warning(f"Path does not exist: {file_path}")
                return None
                
            # Return as string
            return str(path)
        except (ValueError, OSError) as e:
            logger.error(f"Invalid path: {file_path} - {e}")
            return None

