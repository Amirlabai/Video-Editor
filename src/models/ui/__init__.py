"""
UI components for Video Editor application.
"""

from .Dialogs import (
    SettingsDialog, ResolutionDialog, CRFDialog, PresetDialog, EncodingSettingsDialog,
    AudioCodecDialog, AudioBitrateDialog, VideoCodecDialog
)
from .Windows import VideoScalerWindow, BatchWindow, JoinWindow
from .PreviewWindow import PreviewWindow

__all__ = [
    'SettingsDialog',
    'ResolutionDialog', 
    'CRFDialog',
    'PresetDialog',
    'EncodingSettingsDialog',
    'AudioCodecDialog',
    'AudioBitrateDialog',
    'VideoCodecDialog',
    'VideoScalerWindow',
    'BatchWindow',
    'JoinWindow',
    'PreviewWindow'
]

