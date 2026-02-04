"""
Unit tests for constants validation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
from src.models.constants import (
    HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT,
    UHD_4K_WIDTH, UHD_4K_HEIGHT,
    CRF_MIN, CRF_MAX, DEFAULT_CRF,
    DEFAULT_PRESET, PRESET_OPTIONS,
    CPU_CODEC, GPU_CODEC,
    DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE
)


class TestConstants(unittest.TestCase):
    """Test cases for constants validation."""
    
    def test_resolution_values(self):
        """Test resolution constants have valid values."""
        self.assertEqual(HD_WIDTH, 1280)
        self.assertEqual(HD_HEIGHT, 720)
        self.assertEqual(FHD_WIDTH, 1920)
        self.assertEqual(FHD_HEIGHT, 1080)
        self.assertEqual(UHD_4K_WIDTH, 3840)
        self.assertEqual(UHD_4K_HEIGHT, 2160)
        
        # Check aspect ratios
        self.assertAlmostEqual(HD_WIDTH / HD_HEIGHT, 16/9, places=2)
        self.assertAlmostEqual(FHD_WIDTH / FHD_HEIGHT, 16/9, places=2)
        self.assertAlmostEqual(UHD_4K_WIDTH / UHD_4K_HEIGHT, 16/9, places=2)
    
    def test_crf_values(self):
        """Test CRF constants are valid."""
        self.assertGreaterEqual(CRF_MIN, 0)
        self.assertLessEqual(CRF_MAX, 51)  # FFmpeg max CRF
        self.assertGreaterEqual(int(DEFAULT_CRF), CRF_MIN)
        self.assertLessEqual(int(DEFAULT_CRF), CRF_MAX)
    
    def test_preset_options(self):
        """Test preset options are valid."""
        self.assertIn(DEFAULT_PRESET, PRESET_OPTIONS)
        self.assertGreater(len(PRESET_OPTIONS), 0)
        
        # Check common presets exist
        common_presets = ["ultrafast", "fast", "medium", "slow"]
        for preset in common_presets:
            self.assertIn(preset, PRESET_OPTIONS)
    
    def test_codec_values(self):
        """Test codec constants are valid."""
        self.assertIsInstance(CPU_CODEC, str)
        self.assertIsInstance(GPU_CODEC, str)
        self.assertGreater(len(CPU_CODEC), 0)
        self.assertGreater(len(GPU_CODEC), 0)
    
    def test_audio_settings(self):
        """Test audio settings are valid."""
        self.assertIsInstance(DEFAULT_AUDIO_CODEC, str)
        self.assertIsInstance(DEFAULT_AUDIO_BITRATE, str)
        self.assertGreater(len(DEFAULT_AUDIO_CODEC), 0)
        self.assertIn("k", DEFAULT_AUDIO_BITRATE.lower())  # Should have bitrate unit


if __name__ == '__main__':
    unittest.main()

