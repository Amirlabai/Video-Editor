"""
Unit tests for ConfigManager class.
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import unittest
import json
import tempfile
import shutil
from unittest.mock import patch
from models.ConfigManager import ConfigManager
from models.constants import (
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    DEFAULT_CRF, DEFAULT_PRESET
)


def _mock_data_path_factory(temp_dir: str):
    def get_data_path(relative_path: str = "") -> str:
        base = Path(temp_dir)
        if relative_path:
            p = base / relative_path
            p.parent.mkdir(parents=True, exist_ok=True)
            return str(p)
        base.mkdir(parents=True, exist_ok=True)
        return str(base)
    return get_data_path


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.json"

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("models.ConfigManager._legacy_config_path", return_value=Path("/nonexistent/config.json"))
    @patch("utils.core_functions.get_data_path", side_effect=lambda: None)
    def test_default_config_creation(self, mock_gdp, mock_legacy):
        mock_gdp.side_effect = _mock_data_path_factory(self.temp_dir)
        config = ConfigManager()
        window_bg, button_bg, active_bg = config.get_ui_colors()
        self.assertEqual(window_bg, DEFAULT_WINDOW_BG)
        self.assertEqual(button_bg, DEFAULT_BUTTON_BG)
        self.assertEqual(active_bg, DEFAULT_ACTIVE_BUTTON_BG)

    @patch("models.ConfigManager._legacy_config_path", return_value=Path("/nonexistent/config.json"))
    @patch("utils.core_functions.get_data_path")
    def test_load_existing_config(self, mock_gdp, mock_legacy):
        mock_gdp.side_effect = _mock_data_path_factory(self.temp_dir)
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
            "window": {"geometry": "", "state": "normal"}
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        config = ConfigManager()
        window_bg, button_bg, active_bg = config.get_ui_colors()
        self.assertEqual(window_bg, "#000000")
        use_gpu, use_all_cores = config.get_performance_settings()
        self.assertTrue(use_gpu)
        self.assertTrue(use_all_cores)

    @patch("models.ConfigManager._legacy_config_path", return_value=Path("/nonexistent/config.json"))
    @patch("utils.core_functions.get_data_path")
    def test_save_and_load_config(self, mock_gdp, mock_legacy):
        mock_gdp.side_effect = _mock_data_path_factory(self.temp_dir)
        config = ConfigManager()
        config.set_ui_colors("#ff0000", "#00ff00", "#0000ff")
        config.set_performance_settings(True, True)
        config.set_last_input_folder("/custom/input")
        config2 = ConfigManager()
        window_bg, _, _ = config2.get_ui_colors()
        self.assertEqual(window_bg, "#ff0000")
        self.assertEqual(config2.get_last_input_folder(), "/custom/input")

    @patch("models.ConfigManager._legacy_config_path", return_value=Path("/nonexistent/config.json"))
    @patch("utils.core_functions.get_data_path")
    def test_get_encoding_settings_defaults(self, mock_gdp, mock_legacy):
        mock_gdp.side_effect = _mock_data_path_factory(self.temp_dir)
        config = ConfigManager()
        crf, preset, resolution = config.get_encoding_settings()
        self.assertEqual(crf, DEFAULT_CRF)
        self.assertEqual(preset, DEFAULT_PRESET)
        self.assertIn(resolution, ["HD", "FHD", "4K"])


if __name__ == "__main__":
    unittest.main()
