"""
Preview window for showing video information and encoding settings.
"""

import tkinter as tk
from tkinter import scrolledtext
from typing import Optional
from ..VideoInfo import VideoInfo
from ..constants import DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG


class PreviewWindow:
    """Window for previewing video information and encoding settings."""
    
    def __init__(
        self,
        video_path: str,
        encoding_settings: Optional[dict] = None,
        window_bg: str = DEFAULT_WINDOW_BG,
        button_bg: str = DEFAULT_BUTTON_BG,
        active_button_bg: str = DEFAULT_ACTIVE_BUTTON_BG
    ):
        """Initialize PreviewWindow.
        
        Args:
            video_path: Path to video file
            encoding_settings: Dictionary with encoding settings (optional)
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
        """
        self.video_path = video_path
        self.encoding_settings = encoding_settings or {}
        self.window_bg = window_bg
        self.button_bg = button_bg
        self.active_button_bg = active_button_bg
        self.video_info = VideoInfo()
        
        self.window = tk.Toplevel()
        self.window.configure(bg=window_bg)
        self.window.title("Video Preview & Settings")
        self.window.geometry("600x500")
        
        self._create_widgets()
        self._load_video_info()
    
    def _create_widgets(self):
        """Create window widgets."""
        # Title
        title_label = tk.Label(
            self.window, text="📹 Video Preview & Encoding Settings",
            bg=self.window_bg, fg="white", font=("Arial", "16", "bold")
        )
        title_label.pack(pady=10)
        
        # Preview text area
        self.preview_text = scrolledtext.ScrolledText(
            self.window, height=20, width=70,
            bg=self.button_bg, fg="white",
            font=("Courier", "9"), wrap=tk.WORD, relief=tk.FLAT
        )
        self.preview_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Close button
        close_button = tk.Button(
            self.window, text="Close", command=self.window.destroy,
            bg=self.button_bg, fg="white", font=("Arial", "10", "bold"),
            activebackground=self.active_button_bg, activeforeground="white", borderwidth=2
        )
        close_button.pack(pady=10)
    
    def _load_video_info(self):
        """Load and display video information."""
        self.preview_text.insert("end", "=" * 60 + "\n")
        self.preview_text.insert("end", "VIDEO FILE INFORMATION\n")
        self.preview_text.insert("end", "=" * 60 + "\n\n")
        
        # File path
        self.preview_text.insert("end", f"File: {self.video_path}\n\n")
        
        # Get video metadata
        video_metadata = self.video_info.get_video_info(self.video_path)
        total_frames = self.video_info.get_total_frames(self.video_path)
        
        if video_metadata:
            codec, width, height, framerate = video_metadata
            self.preview_text.insert("end", "Video Properties:\n")
            self.preview_text.insert("end", f"  • Codec: {codec}\n")
            self.preview_text.insert("end", f"  • Resolution: {width}x{height}\n")
            self.preview_text.insert("end", f"  • Frame Rate: {framerate}\n")
            if total_frames:
                self.preview_text.insert("end", f"  • Total Frames: {total_frames:,}\n")
            self.preview_text.insert("end", "\n")
        else:
            self.preview_text.insert("end", "Could not read video metadata\n\n")
        
        # Encoding settings preview
        if self.encoding_settings:
            self.preview_text.insert("end", "=" * 60 + "\n")
            self.preview_text.insert("end", "ENCODING SETTINGS PREVIEW\n")
            self.preview_text.insert("end", "=" * 60 + "\n\n")
            
            # Resolution
            if "width" in self.encoding_settings and "height" in self.encoding_settings:
                self.preview_text.insert("end", f"Output Resolution: {self.encoding_settings['width']}x{self.encoding_settings['height']}\n")
            
            # Quality
            if "crf" in self.encoding_settings:
                self.preview_text.insert("end", f"Quality (CRF): {self.encoding_settings['crf']}\n")
            
            # Preset
            if "preset" in self.encoding_settings:
                self.preview_text.insert("end", f"Preset: {self.encoding_settings['preset']}\n")
            
            # Codec
            if "video_codec" in self.encoding_settings:
                self.preview_text.insert("end", f"🎬 Video Codec: {self.encoding_settings['video_codec']}\n")
            
            if "audio_codec" in self.encoding_settings:
                self.preview_text.insert("end", f"🔊 Audio Codec: {self.encoding_settings['audio_codec']}\n")
            
            if "audio_bitrate" in self.encoding_settings:
                self.preview_text.insert("end", f"🔊 Audio Bitrate: {self.encoding_settings['audio_bitrate']}\n")
            
            # Orientation
            if "orientation" in self.encoding_settings:
                self.preview_text.insert("end", f"📱 Orientation: {self.encoding_settings['orientation']}\n")
        
        self.preview_text.config(state=tk.DISABLED)
    
    @staticmethod
    def show(
        video_path: str,
        encoding_settings: Optional[dict] = None,
        window_bg: str = DEFAULT_WINDOW_BG,
        button_bg: str = DEFAULT_BUTTON_BG,
        active_button_bg: str = DEFAULT_ACTIVE_BUTTON_BG
    ):
        """Show preview window.
        
        Args:
            video_path: Path to video file
            encoding_settings: Dictionary with encoding settings (optional)
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
        """
        preview = PreviewWindow(video_path, encoding_settings, window_bg, button_bg, active_button_bg)
        preview.window.mainloop()

