"""
Unit tests for ConfigManager class.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
import json
import tempfile
from unittest.mock import patch, mock_open
from src.models.ConfigManager import ConfigManager
from src.models.constants import (
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    DEFAULT_CRF, DEFAULT_PRESET
)


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".video_editor"
        self.config_file = self.config_dir / "config.json"
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('src.models.ConfigManager.Path.home')
    def test_default_config_creation(self, mock_home):
        """Test default config is created when file doesn't exist."""
        mock_home.return_value = Path(self.temp_dir)
        
        # Create config directory but not file
        self.config_dir.mkdir(exist_ok=True)
        
        config = ConfigManager()
        
        # Check default values
        window_bg, button_bg, active_bg = config.get_ui_colors()
        self.assertEqual(window_bg, DEFAULT_WINDOW_BG)
        self.assertEqual(button_bg, DEFAULT_BUTTON_BG)
        self.assertEqual(active_bg, DEFAULT_ACTIVE_BUTTON_BG)
    
    @patch('src.models.ConfigManager.Path.home')
    def test_load_existing_config(self, mock_home):
        """Test loading existing config file."""
        mock_home.return_value = Path(self.temp_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Create config file with custom values
        config_data = {
            "ui": {
                "window_bg": "#000000",
                "button_bg": "#111111",
                "active_button_bg": "#222222"
            },
            "performance": {
                "use_gpu": True,
                "use_all_cores": True,
                "cpu_cores": 8
            },
            "encoding": {
                "default_crf": "24",
                "default_preset": "slow",
                "default_resolution": "4K"
            },
            "folders": {
                "last_input_folder": "/test/input",
                "last_output_folder": "/test/output"
            },
            "window": {
                "geometry": "",
                "state": "normal"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = ConfigManager()
        
        window_bg, button_bg, active_bg = config.get_ui_colors()
        self.assertEqual(window_bg, "#000000")
        self.assertEqual(button_bg, "#111111")
        self.assertEqual(active_bg, "#222222")
        
        use_gpu, use_all_cores = config.get_performance_settings()
        self.assertTrue(use_gpu)
        self.assertTrue(use_all_cores)
    
    @patch('src.models.ConfigManager.Path.home')
    def test_save_and_load_config(self, mock_home):
        """Test saving and loading configuration."""
        mock_home.return_value = Path(self.temp_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        config = ConfigManager()
        
        # Set some values
        config.set_ui_colors("#ff0000", "#00ff00", "#0000ff")
        config.set_performance_settings(True, True)
        config.set_last_input_folder("/custom/input")
        
        # Create new instance to test persistence
        config2 = ConfigManager()
        
        window_bg, button_bg, active_bg = config2.get_ui_colors()
        self.assertEqual(window_bg, "#ff0000")
        self.assertEqual(button_bg, "#00ff00")
        self.assertEqual(active_bg, "#0000ff")
        
        use_gpu, use_all_cores = config2.get_performance_settings()
        self.assertTrue(use_gpu)
        self.assertTrue(use_all_cores)
        
        self.assertEqual(config2.get_last_input_folder(), "/custom/input")
    
    @patch('src.models.ConfigManager.Path.home')
    def test_get_encoding_settings_defaults(self, mock_home):
        """Test getting default encoding settings."""
        mock_home.return_value = Path(self.temp_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        config = ConfigManager()
        crf, preset, resolution = config.get_encoding_settings()
        
        self.assertEqual(crf, DEFAULT_CRF)
        self.assertEqual(preset, DEFAULT_PRESET)
        self.assertIn(resolution, ["HD", "FHD", "4K"])


if __name__ == '__main__':
    unittest.main()

