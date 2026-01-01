"""
Unit tests for FFmpegCommandBuilder class.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
from src.models.FFmpegCommandBuilder import FFmpegCommandBuilder
from src.models.constants import (
    HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT,
    DEFAULT_CRF, DEFAULT_PRESET, CPU_CODEC, GPU_CODEC,
    DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE
)


class TestFFmpegCommandBuilder(unittest.TestCase):
    """Test cases for FFmpegCommandBuilder class."""
    
    def test_build_scale_command_cpu_basic(self):
        """Test basic CPU scale command building."""
        cmd = FFmpegCommandBuilder.build_scale_command_cpu(
            "input.mp4", "output.mp4"
        )
        
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-i", cmd)
        self.assertIn("input.mp4", cmd)
        self.assertIn("output.mp4", cmd)
        self.assertIn("-c:v", cmd)
        self.assertIn(CPU_CODEC, cmd)
        self.assertIn("-crf", cmd)
        self.assertIn(DEFAULT_CRF, cmd)
        self.assertIn("-preset", cmd)
        self.assertIn(DEFAULT_PRESET, cmd)
    
    def test_build_scale_command_cpu_with_threads(self):
        """Test CPU scale command with thread count."""
        cmd = FFmpegCommandBuilder.build_scale_command_cpu(
            "input.mp4", "output.mp4", threads=4
        )
        
        self.assertIn("-threads", cmd)
        self.assertIn("4", cmd)
        self.assertEqual(cmd[cmd.index("-threads") + 1], "4")
    
    def test_build_scale_command_cpu_custom_resolution(self):
        """Test CPU scale command with custom resolution."""
        cmd = FFmpegCommandBuilder.build_scale_command_cpu(
            "input.mp4", "output.mp4",
            xaxis=str(FHD_WIDTH), yaxis=str(FHD_HEIGHT)
        )
        
        self.assertIn("-vf", cmd)
        # Check if any command element contains the scale filter
        self.assertTrue(any(f"scale={FHD_WIDTH}:{FHD_HEIGHT}" in str(arg) for arg in cmd))
    
    def test_build_scale_command_gpu_basic(self):
        """Test basic GPU scale command building."""
        cmd = FFmpegCommandBuilder.build_scale_command_gpu(
            "input.mp4", "output.mp4"
        )
        
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-hwaccel", cmd)
        self.assertIn("cuda", cmd)
        self.assertIn("-c:v", cmd)
        self.assertIn(GPU_CODEC, cmd)
        self.assertIn("-cq", cmd)  # GPU uses -cq instead of -crf
        self.assertIn("-vf", cmd)
        # Check if any command element contains "scale_cuda"
        self.assertTrue(any("scale_cuda" in str(arg) for arg in cmd))
    
    def test_build_scale_command_gpu_custom_settings(self):
        """Test GPU scale command with custom settings."""
        cmd = FFmpegCommandBuilder.build_scale_command_gpu(
            "input.mp4", "output.mp4",
            xaxis="2560", yaxis="1440",
            crf="24", preset="fast"
        )
        
        # Check if any command element contains the scale filter
        self.assertTrue(any("scale_cuda=2560:1440" in str(arg) for arg in cmd))
        self.assertIn("24", cmd)
        self.assertIn("fast", cmd)
    
    def test_build_concat_command(self):
        """Test concat command building."""
        cmd = FFmpegCommandBuilder.build_concat_command(
            "concat_list.txt", "output.mp4"
        )
        
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-f", cmd)
        self.assertIn("concat", cmd)
        self.assertIn("-safe", cmd)
        self.assertIn("0", cmd)
        self.assertIn("-i", cmd)
        self.assertIn("concat_list.txt", cmd)
        self.assertIn("-c", cmd)
        self.assertIn("copy", cmd)
        self.assertIn("output.mp4", cmd)
    
    def test_build_scale_command_cpu_audio_settings(self):
        """Test CPU command includes audio settings."""
        cmd = FFmpegCommandBuilder.build_scale_command_cpu(
            "input.mp4", "output.mp4"
        )
        
        self.assertIn("-c:a", cmd)
        self.assertIn(DEFAULT_AUDIO_CODEC, cmd)
        self.assertIn("-b:a", cmd)
        self.assertIn(DEFAULT_AUDIO_BITRATE, cmd)
    
    def test_build_scale_command_progress_output(self):
        """Test that commands include progress output."""
        cmd_cpu = FFmpegCommandBuilder.build_scale_command_cpu(
            "input.mp4", "output.mp4"
        )
        cmd_gpu = FFmpegCommandBuilder.build_scale_command_gpu(
            "input.mp4", "output.mp4"
        )
        
        self.assertIn("-progress", cmd_cpu)
        self.assertIn("pipe:1", cmd_cpu)
        self.assertIn("-progress", cmd_gpu)
        self.assertIn("pipe:1", cmd_gpu)


if __name__ == '__main__':
    unittest.main()

