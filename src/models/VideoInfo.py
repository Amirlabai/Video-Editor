"""
VideoInfo class for extracting video metadata using ffprobe.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class VideoInfo:
    """Handles video metadata extraction and information retrieval.
    
    This class stores video information and user selections as instance state.
    """
    
    def __init__(self, video_path: Optional[str] = None):
        """Initialize VideoInfo object.
        
        Args:
            video_path: Optional path to video file to load immediately
        """
        # Video file path
        self.video_path: Optional[str] = None
        
        # Video metadata (extracted from file)
        self.fps: Optional[float] = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.codec: Optional[str] = None
        self.framerate: Optional[str] = None  # Raw framerate string from ffprobe
        self.total_frames: Optional[int] = None
        self.status_done: Optional[str] = None
        
        # User selections - encoding settings
        self.target_fps: Optional[float] = None
        self.target_width: Optional[int] = None
        self.target_height: Optional[int] = None
        self.is_vertical: bool = False
        self.orientation: str = "_horizontal"  # "_horizontal" or "_vertical"
        self.crf: Optional[str] = None
        self.preset: Optional[str] = None
        
        # Performance settings
        self.use_gpu: bool = False
        self.use_all_cores: bool = False
        self.cap_cpu_50: bool = False
        self.cpu_cores: Optional[int] = None  # System CPU core count
        
        # Load video if path provided
        if video_path:
            self.load_video(video_path)
    
    def load_video(self, video_path: str) -> bool:
        """Load video information from file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            True if successful, False otherwise
        """
        self.video_path = video_path
        
        # Extract codec and framerate
        video_info = self._extract_video_info(video_path)
        if video_info:
            self.codec, self.width, self.height, self.framerate = video_info
            if self.width < self.height:
                self.is_vertical = True
                self.orientation = "_vertical"
            else:
                self.is_vertical = False
                self.orientation = "_horizontal"
            # Use width/height from video_info if fps_info didn't work
            self.fps = self._parse_framerate(self.framerate) if self.framerate else None
        
        # Extract total frames
        self.total_frames = self._extract_total_frames(video_path)
        
        return self.fps is not None and self.width is not None and self.height is not None
    
    def _parse_framerate(self, framerate_str: str) -> Optional[float]:
        """Parse framerate string to float.
        
        Args:
            framerate_str: Framerate string (e.g., "30/1" or "29.97/1")
            
        Returns:
            FPS as float, or None if parsing fails
        """
        try:
            if "/" in framerate_str:
                num, den = framerate_str.split("/")
                return float(num) / float(den)
            else:
                return float(framerate_str)
        except (ValueError, ZeroDivisionError):
            return None
    
    def _extract_fps_and_size(self, video_path: str) -> Optional[Tuple[float, int, int]]:
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
            
            fps = self._parse_framerate(framerate_str)
            if fps is None:
                return None
            
            return fps, width, height
        except Exception as e:
            logger.error(f"Error getting FPS and size for {video_path}: {e}")
            return None
    
    def _extract_video_info(self, video_path: str) -> Optional[Tuple[str, int, int, str]]:
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
    
    def _extract_total_frames(self, video_path: str) -> Optional[int]:
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
    
    def get_duration(self, video_path: Optional[str] = None) -> Optional[float]:
        """Get video duration in seconds.
        
        Args:
            video_path: Optional path to video file (uses self.video_path if not provided)
            
        Returns:
            Duration in seconds, or None if extraction fails
        """
        path = video_path or self.video_path
        if not path:
            return None
        
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration_str = result.stdout.strip()
            if duration_str:
                return float(duration_str)
            return None
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            logger.error(f"Error getting duration for {path}: {e}")
            return None
    
    # Convenience methods for backward compatibility and easy access
    def get_total_frames(self, video_path: Optional[str] = None) -> Optional[int]:
        """Get total frames. Uses stored value if available, otherwise extracts from video_path.
        
        Args:
            video_path: Optional path to video file (uses self.video_path if not provided)
            
        Returns:
            Total number of frames, or None if extraction fails
        """
        if self.total_frames is not None:
            return self.total_frames
        
        path = video_path or self.video_path
        if path:
            self.total_frames = self._extract_total_frames(path)
            return self.total_frames
        
        return None
    
    def get_fps_and_size(self, video_path: Optional[str] = None) -> Optional[Tuple[float, int, int]]:
        """Get FPS and size. Uses stored values if available, otherwise extracts from video_path.
        
        Args:
            video_path: Optional path to video file (uses self.video_path if not provided)
            
        Returns:
            Tuple of (fps, width, height) or None if extraction fails
        """
        if self.fps is not None and self.width is not None and self.height is not None:
            return (self.fps, self.width, self.height)
        
        path = video_path or self.video_path
        if path:
            result = self._extract_fps_and_size(path)
            if result:
                self.fps, self.width, self.height = result
                return result
        
        return None
    
    def get_video_info(self, video_path: Optional[str] = None) -> Optional[Tuple[str, int, int, str]]:
        """Get video info. Uses stored values if available, otherwise extracts from video_path.
        
        Args:
            video_path: Optional path to video file (uses self.video_path if not provided)
            
        Returns:
            Tuple of (codec, width, height, framerate) or None if extraction fails
        """
        if (self.codec is not None and self.width is not None and 
            self.height is not None and self.framerate is not None):
            return (self.codec, self.width, self.height, self.framerate)
        
        path = video_path or self.video_path
        if path:
            result = self._extract_video_info(path)
            if result:
                self.codec, self.width, self.height, self.framerate = result
                return result
        
        return None
    
    # Methods to set user selections
    def set_target_fps(self, target_fps: Optional[float]) -> None:
        """Set target FPS selection."""
        self.target_fps = target_fps
    
    def set_target_resolution(self, width: Optional[int], height: Optional[int], is_vertical: bool = False) -> None:
        """Set target resolution selection.
        
        Args:
            width: Target width
            height: Target height
            is_vertical: Whether orientation is vertical
        """
        self.target_width = width
        self.target_height = height
        self.is_vertical = is_vertical
        self.orientation = "_vertical" if is_vertical else "_horizontal"
    
    def get_target_resolution(self) -> Tuple[Optional[int], Optional[int]]:
        """Get target resolution.
        
        Returns:
            Tuple of (width, height) or (None, None) if not set
        """
        return (self.target_width, self.target_height)
    
    def set_encoding_settings(self, crf: Optional[str] = None, preset: Optional[str] = None) -> None:
        """Set encoding settings.
        
        Args:
            crf: Constant Rate Factor
            preset: Encoding preset
        """
        if crf is not None:
            self.crf = crf
        if preset is not None:
            self.preset = preset
    
    def set_performance_settings(self, use_gpu: bool = False, use_all_cores: bool = False, cap_cpu_50: bool = False) -> None:
        """Set performance settings.
        
        Args:
            use_gpu: Whether to use GPU encoding
            use_all_cores: Whether to use all CPU cores
            cap_cpu_50: Whether to cap CPU usage at 50%
        """
        self.use_gpu = use_gpu
        self.use_all_cores = use_all_cores
        self.cap_cpu_50 = cap_cpu_50
    
    def get_all_settings(self) -> dict:
        """Get all user settings as a dictionary.
        
        Returns:
            Dictionary containing all user settings
        """
        return {
            'target_fps': self.target_fps,
            'target_width': self.target_width,
            'target_height': self.target_height,
            'is_vertical': self.is_vertical,
            'orientation': self.orientation,
            'crf': self.crf,
            'preset': self.preset,
            'use_gpu': self.use_gpu,
            'use_all_cores': self.use_all_cores,
            'cap_cpu_50': self.cap_cpu_50
        }
    
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
        
        # Create VideoInfo instance for reference video
        reference_video_info = VideoInfo(video_files[0])
        reference_info = reference_video_info.get_video_info()
        if not reference_info:
            return False

        # Check all other videos against reference
        for video in video_files[1:]:
            video_info = VideoInfo(video)
            info = video_info.get_video_info()
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

