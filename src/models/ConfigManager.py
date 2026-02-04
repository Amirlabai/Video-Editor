"""
Configuration Manager for Video Editor application.
Handles saving and loading user preferences to/from JSON file.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging
from .constants import (
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    DEFAULT_CRF, DEFAULT_PRESET, CONFIG_DIR_NAME, CONFIG_FILENAME
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration and user preferences."""
    
    def __init__(self):
        """Initialize ConfigManager and load configuration."""
        self.config_dir = Path.home() / CONFIG_DIR_NAME
        self.config_file = self.config_dir / CONFIG_FILENAME
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "ui": {
                "window_bg": DEFAULT_WINDOW_BG,
                "button_bg": DEFAULT_BUTTON_BG,
                "active_button_bg": DEFAULT_ACTIVE_BUTTON_BG
            },
            "performance": {
                "use_gpu": False,
                "use_all_cores": False,
                "cpu_cores": 0,  # Will be set dynamically
                "cap_cpu_50": False
            },
            "video": {
                "target_fps": None  # None to keep current, or float value
            },
            "encoding": {
                "default_crf": DEFAULT_CRF,
                "default_preset": DEFAULT_PRESET,
                "default_resolution": "FHD"  # HD, FHD, or 4K
            },
            "folders": {
                "last_input_folder": "",
                "last_output_folder": "",
                "last_join_input_folder": "",
                "last_join_output_folder": ""
            },
            "window": {
                "geometry": "",
                "state": "normal"  # normal, maximized, etc.
            }
        }
    
    def _load_config(self) -> None:
        """Load configuration from file, or create default if file doesn't exist."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_config = self._get_default_config()
                    self.config = self._merge_config(default_config, loaded_config)
                    logger.info(f"Configuration loaded from {self.config_file}")
            else:
                # Create default config
                self.config = self._get_default_config()
                self._save_config()
                logger.info("Created default configuration file")
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.error(f"Error loading configuration: {e}. Using defaults.")
            self.config = self._get_default_config()
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge loaded config with defaults."""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(exist_ok=True)
            
            # Save to temporary file first, then rename (atomic operation)
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            # Replace original file
            if self.config_file.exists():
                self.config_file.unlink()
            temp_file.rename(self.config_file)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except (IOError, OSError) as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    # UI Settings
    def get_ui_colors(self) -> Tuple[str, str, str]:
        """Get UI color settings.
        
        Returns:
            tuple: (window_bg, button_bg, active_button_bg)
        """
        ui = self.config.get("ui", {})
        return (
            ui.get("window_bg", DEFAULT_WINDOW_BG),
            ui.get("button_bg", DEFAULT_BUTTON_BG),
            ui.get("active_button_bg", DEFAULT_ACTIVE_BUTTON_BG)
        )
    
    def set_ui_colors(self, window_bg: str, button_bg: str, active_button_bg: str) -> None:
        """Set UI color settings."""
        if "ui" not in self.config:
            self.config["ui"] = {}
        self.config["ui"]["window_bg"] = window_bg
        self.config["ui"]["button_bg"] = button_bg
        self.config["ui"]["active_button_bg"] = active_button_bg
        self._save_config()
    
    # Performance Settings
    def get_performance_settings(self) -> Tuple[bool, bool]:
        """Get performance settings.
        
        Returns:
            tuple: (use_gpu, use_all_cores)
        """
        perf = self.config.get("performance", {})
        return (
            perf.get("use_gpu", False),
            perf.get("use_all_cores", False)
        )
    
    def set_performance_settings(self, use_gpu: bool, use_all_cores: bool, cap_cpu_50: bool = False) -> None:
        """Set performance settings."""
        if "performance" not in self.config:
            self.config["performance"] = {}
        self.config["performance"]["use_gpu"] = use_gpu
        self.config["performance"]["use_all_cores"] = use_all_cores
        self.config["performance"]["cap_cpu_50"] = cap_cpu_50
        self._save_config()
    
    def get_cpu_cap_setting(self) -> bool:
        """Get CPU cap setting."""
        perf = self.config.get("performance", {})
        return perf.get("cap_cpu_50", False)
    
    def set_target_fps(self, target_fps: Optional[float]) -> None:
        """Set target FPS setting."""
        if "video" not in self.config:
            self.config["video"] = {}
        self.config["video"]["target_fps"] = target_fps
        self._save_config()
    
    def get_target_fps(self) -> Optional[float]:
        """Get target FPS setting."""
        video = self.config.get("video", {})
        fps = video.get("target_fps")
        return float(fps) if fps is not None else None
    
    # Encoding Settings
    def get_encoding_settings(self) -> Tuple[str, str, str]:
        """Get encoding settings.
        
        Returns:
            tuple: (crf, preset, resolution)
        """
        enc = self.config.get("encoding", {})
        return (
            enc.get("default_crf", DEFAULT_CRF),
            enc.get("default_preset", DEFAULT_PRESET),
            enc.get("default_resolution", "FHD")
        )
    
    def set_encoding_settings(self, crf: str, preset: str, resolution: str) -> None:
        """Set encoding settings."""
        if "encoding" not in self.config:
            self.config["encoding"] = {}
        self.config["encoding"]["default_crf"] = crf
        self.config["encoding"]["default_preset"] = preset
        self.config["encoding"]["default_resolution"] = resolution
        self._save_config()
    
    # Folder Settings
    def get_last_input_folder(self) -> str:
        """Get last used input folder."""
        return self.config.get("folders", {}).get("last_input_folder", "")
    
    def set_last_input_folder(self, folder: str) -> None:
        """Set last used input folder."""
        if "folders" not in self.config:
            self.config["folders"] = {}
        self.config["folders"]["last_input_folder"] = folder
        self._save_config()
    
    def get_last_output_folder(self) -> str:
        """Get last used output folder."""
        return self.config.get("folders", {}).get("last_output_folder", "")
    
    def set_last_output_folder(self, folder: str) -> None:
        """Set last used output folder."""
        if "folders" not in self.config:
            self.config["folders"] = {}
        self.config["folders"]["last_output_folder"] = folder
        self._save_config()
    
    def get_last_join_input_folder(self) -> str:
        """Get last used join input folder."""
        return self.config.get("folders", {}).get("last_join_input_folder", "")
    
    def set_last_join_input_folder(self, folder: str) -> None:
        """Set last used join input folder."""
        if "folders" not in self.config:
            self.config["folders"] = {}
        self.config["folders"]["last_join_input_folder"] = folder
        self._save_config()
    
    def get_last_join_output_folder(self) -> str:
        """Get last used join output folder."""
        return self.config.get("folders", {}).get("last_join_output_folder", "")
    
    def set_last_join_output_folder(self, folder: str) -> None:
        """Set last used join output folder."""
        if "folders" not in self.config:
            self.config["folders"] = {}
        self.config["folders"]["last_join_output_folder"] = folder
        self._save_config()
    
    # Window Settings
    def get_window_geometry(self) -> str:
        """Get saved window geometry."""
        return self.config.get("window", {}).get("geometry", "")
    
    def set_window_geometry(self, geometry: str) -> None:
        """Set window geometry."""
        if "window" not in self.config:
            self.config["window"] = {}
        self.config["window"]["geometry"] = geometry
        self._save_config()
    
    def get_window_state(self) -> str:
        """Get saved window state."""
        return self.config.get("window", {}).get("state", "normal")
    
    def set_window_state(self, state: str) -> None:
        """Set window state."""
        if "window" not in self.config:
            self.config["window"] = {}
        self.config["window"]["state"] = state
        self._save_config()
    
    # Generic get/set methods
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation (e.g., 'ui.window_bg').
        
        Args:
            key_path: Dot-separated path to the config value
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """Set a configuration value using dot notation (e.g., 'ui.window_bg').
        
        Args:
            key_path: Dot-separated path to the config value
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self._save_config()
    
    def get_config_file_path(self) -> str:
        """Get the path to the configuration file.
        
        Returns:
            str: Absolute path to the config file
        """
        return str(self.config_file)
    
    def get_config_dir_path(self) -> str:
        """Get the path to the configuration directory.
        
        Returns:
            str: Absolute path to the config directory
        """
        return str(self.config_dir)
    
    def open_config_in_editor(self) -> bool:
        """Open the config file in the system's default text editor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        import subprocess
        import platform as plat
        
        try:
            if plat.system() == 'Windows':
                os.startfile(self.config_file)
            elif plat.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(self.config_file)])
            else:  # Linux
                subprocess.run(['xdg-open', str(self.config_file)])
            return True
        except Exception as e:
            logger.error(f"Error opening config file: {e}")
            return False


# Global instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance (singleton pattern)."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

