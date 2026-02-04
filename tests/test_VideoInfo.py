"""
Unit tests for VideoInfo class.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
from unittest.mock import patch, MagicMock
from src.models.VideoInfo import VideoInfo


class TestVideoInfo(unittest.TestCase):
    """Test cases for VideoInfo class."""
    
    @patch('src.models.VideoInfo.subprocess.run')
    def test_get_total_frames_success(self, mock_run):
        """Test successful frame count extraction."""
        # Mock ffprobe output: fps on first line, duration on second
        mock_result = MagicMock()
        mock_result.stdout = "30/1\n120.5\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        frames = VideoInfo.get_total_frames("test_video.mp4")
        
        # Code does: int(int(float("120.5")) * int("30")) = int(120 * 30) = 3600
        # The int() truncates the duration, so 120.5 becomes 120
        self.assertEqual(frames, 3600)  # int(120.5) * 30 = 120 * 30 = 3600
        mock_run.assert_called_once()
    
    @patch('src.models.VideoInfo.subprocess.run')
    def test_get_total_frames_ffprobe_error(self, mock_run):
        """Test frame extraction when ffprobe fails."""
        mock_run.side_effect = FileNotFoundError("ffprobe not found")
        
        frames = VideoInfo.get_total_frames("test_video.mp4")
        
        self.assertIsNone(frames)
    
    @patch('src.models.VideoInfo.subprocess.run')
    def test_get_video_info_success(self, mock_run):
        """Test successful video info extraction."""
        mock_result = MagicMock()
        mock_result.stdout = "h264\n1920\n1080\n30/1\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        info = VideoInfo.get_video_info("test_video.mp4")
        
        self.assertIsNotNone(info)
        self.assertEqual(info[0], "h264")
        self.assertEqual(info[1], 1920)
        self.assertEqual(info[2], 1080)
        self.assertEqual(info[3], "30/1")
    
    @patch('src.models.VideoInfo.subprocess.run')
    def test_get_video_info_failure(self, mock_run):
        """Test video info extraction failure."""
        mock_run.side_effect = Exception("Error")
        
        info = VideoInfo.get_video_info("test_video.mp4")
        
        self.assertIsNone(info)
    
    @patch('src.models.VideoInfo.VideoInfo.get_video_info')
    def test_check_compatibility_all_match(self, mock_get_info):
        """Test compatibility check when all videos match."""
        mock_get_info.return_value = ("h264", 1920, 1080, "30/1")
        
        video_files = ["video1.mp4", "video2.mp4", "video3.mp4"]
        result = VideoInfo.check_compatibility(video_files)
        
        self.assertTrue(result)
        self.assertEqual(mock_get_info.call_count, 3)
    
    @patch('src.models.VideoInfo.VideoInfo.get_video_info')
    def test_check_compatibility_mismatch(self, mock_get_info):
        """Test compatibility check when videos don't match."""
        mock_get_info.side_effect = [
            ("h264", 1920, 1080, "30/1"),
            ("h264", 1280, 720, "30/1")  # Different resolution
        ]
        
        video_files = ["video1.mp4", "video2.mp4"]
        result = VideoInfo.check_compatibility(video_files)
        
        self.assertFalse(result)
    
    def test_check_compatibility_empty_list(self):
        """Test compatibility check with empty list."""
        result = VideoInfo.check_compatibility([])
        self.assertFalse(result)
    
    @patch('src.models.VideoInfo.Path')
    def test_sanitize_path_valid(self, mock_path):
        """Test path sanitization with valid path."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path.return_value = mock_path_instance
        mock_path_instance.__str__ = lambda x: "/valid/path/video.mp4"
        
        result = VideoInfo.sanitize_path("video.mp4")
        
        self.assertIsNotNone(result)
    
    @patch('src.models.VideoInfo.Path')
    def test_sanitize_path_nonexistent(self, mock_path):
        """Test path sanitization with nonexistent path."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path.return_value = mock_path_instance
        
        result = VideoInfo.sanitize_path("nonexistent.mp4")
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()

