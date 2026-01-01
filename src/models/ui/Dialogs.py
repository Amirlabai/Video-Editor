"""
Dialog classes for Video Editor application.
"""

import tkinter as tk
import subprocess
import multiprocessing
from typing import Tuple, Optional
from ..ConfigManager import get_config_manager
from ..constants import (
    HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT, UHD_4K_WIDTH, UHD_4K_HEIGHT,
    CRF_MIN, CRF_MAX, DEFAULT_CRF, HIGH_QUALITY_CRF, DEFAULT_PRESET, PRESET_OPTIONS,
    DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE, AUDIO_CODEC_OPTIONS, AUDIO_BITRATE_OPTIONS,
    CPU_CODEC, CPU_CODEC_OPTIONS, GPU_CODEC, GPU_CODEC_OPTIONS
)


class SettingsDialog:
    """Dialog for performance settings (GPU/CPU, threading)."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332'
    ) -> Tuple[bool, bool, int]:
        """Show performance settings dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            
        Returns:
            Tuple of (use_gpu, use_all_cores, cpu_cores)
        """
        config = get_config_manager()
        default_use_gpu, default_use_all_cores = config.get_performance_settings()
        
        perf_window = tk.Toplevel(root)
        perf_window.configure(bg=window_bg)
        perf_window.title("Performance Settings")
        perf_window.grab_set()
        
        use_gpu = tk.BooleanVar(perf_window, value=default_use_gpu)
        use_all_cores = tk.BooleanVar(perf_window, value=default_use_all_cores)
        gpu_available = SettingsDialog._check_gpu_compatibility()
        cpu_cores = multiprocessing.cpu_count()
        
        def confirm_settings():
            config.set_performance_settings(use_gpu.get(), use_all_cores.get())
            perf_window.destroy()
        
        # GPU option
        if gpu_available:
            gpu_label = tk.Label(perf_window, text="🚀 GPU (NVENC) Available!", 
                                bg=window_bg, fg="#4CAF50", font=("Arial", "12", "bold"))
            gpu_label.grid(row=0, column=0, columnspan=2, pady=10, padx=10)
            
            gpu_checkbox = tk.Checkbutton(perf_window, text="Use GPU encoding (Much Faster!)", 
                                          variable=use_gpu, bg=window_bg, fg="white",
                                          selectcolor=active_button_bg, font=("Arial", "10", "bold"))
            gpu_checkbox.grid(row=1, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        else:
            gpu_label = tk.Label(perf_window, text="⚠️ GPU (NVENC) Not Available", 
                                bg=window_bg, fg="#FF9800", font=("Arial", "12", "bold"))
            gpu_label.grid(row=0, column=0, columnspan=2, pady=10, padx=10)
            
            gpu_info = tk.Label(perf_window, text="Using CPU encoding", bg=window_bg, fg="white", 
                               font=("Arial", "9"))
            gpu_info.grid(row=1, column=0, columnspan=2, pady=5, padx=10)
        
        # Threading option
        threading_label = tk.Label(perf_window, text="CPU Threading", bg=window_bg, fg="white", 
                                  font=("Arial", "12", "bold"))
        threading_label.grid(row=2, column=0, columnspan=2, pady=(20, 5), padx=10)
        
        cores_info = tk.Label(perf_window, text=f"Available CPU cores: {cpu_cores}", 
                             bg=window_bg, fg="white", font=("Arial", "9"))
        cores_info.grid(row=3, column=0, columnspan=2, pady=5, padx=10)
        
        threading_checkbox = tk.Checkbutton(perf_window, 
                                            text=f"Use all CPU cores (Default: FFmpeg auto, All cores: {cpu_cores} threads)", 
                                            variable=use_all_cores, bg=window_bg, fg="white",
                                            selectcolor=active_button_bg, font=("Arial", "10", "bold"))
        threading_checkbox.grid(row=4, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        
        # Confirm button
        confirm_button = tk.Button(perf_window, text="Confirm", command=confirm_settings, 
                                  bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                                  activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        confirm_button.grid(row=5, column=0, columnspan=2, pady=20, padx=10)
        
        perf_window.wait_window()
        
        return use_gpu.get(), use_all_cores.get(), cpu_cores
    
    @staticmethod
    def _check_gpu_compatibility() -> bool:
        """Check if GPU (NVENC) is available."""
        try:
            cmd = ["ffmpeg", "-hide_banner", "-encoders"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            return "h264_nvenc" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False


class ResolutionDialog:
    """Dialog for resolution selection."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332'
    ) -> Tuple[str, str]:
        """Show resolution selection dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            
        Returns:
            Tuple of (width, height) as strings
        """
        res_window = tk.Toplevel(root)
        res_window.configure(bg=window_bg)
        res_window.title("Video Resolution")
        res_window.grab_set()
        
        selected_res = [None, None]
        
        def set_hd():
            selected_res[0] = str(HD_WIDTH)
            selected_res[1] = str(HD_HEIGHT)
            res_window.destroy()
        
        def set_fhd():
            selected_res[0] = str(FHD_WIDTH)
            selected_res[1] = str(FHD_HEIGHT)
            res_window.destroy()
        
        def set_4k():
            selected_res[0] = str(UHD_4K_WIDTH)
            selected_res[1] = str(UHD_4K_HEIGHT)
            res_window.destroy()
        
        label = tk.Label(res_window, text="Video Resolution", bg=window_bg, fg="white", 
                        font=("Arial", "16", "bold"))
        label.pack(pady=10)
        
        hd_button = tk.Button(res_window, text=f"HD: {HD_WIDTH}x{HD_HEIGHT}", command=set_hd,
                             bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                             activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        hd_button.pack(pady=5)
        
        fhd_button = tk.Button(res_window, text=f"FHD: {FHD_WIDTH}x{FHD_HEIGHT}", command=set_fhd,
                              bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                              activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        fhd_button.pack(pady=5)
        
        k4_button = tk.Button(res_window, text=f"4K: {UHD_4K_WIDTH}x{UHD_4K_HEIGHT}", command=set_4k,
                             bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                             activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        k4_button.pack(pady=5)
        
        res_window.wait_window()
        
        if selected_res[0] is None:
            return str(HD_WIDTH), str(HD_HEIGHT)
        return selected_res[0], selected_res[1]


class CRFDialog:
    """Dialog for CRF (quality) selection."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332'
    ) -> str:
        """Show CRF selection dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            
        Returns:
            CRF value as string
        """
        crf_window = tk.Toplevel(root)
        crf_window.configure(bg=window_bg)
        crf_window.title("Video Encoding")
        crf_window.grab_set()
        
        crf_value = tk.StringVar(crf_window, value=str(DEFAULT_CRF))
        
        def set_crf():
            crf_window.destroy()
        
        label = tk.Label(crf_window, text="Video Encoding", bg=window_bg, fg="white", 
                        font=("Arial", "16", "bold"))
        label.pack(pady=10)
        
        label_2 = tk.Label(crf_window, text="the lower the better", bg=window_bg, fg="white", 
                          font=("Arial", "10", "bold"))
        label_2.pack()
        
        slider = tk.Scale(crf_window, from_=CRF_MIN, to=CRF_MAX, orient=tk.HORIZONTAL, 
                         bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                         activebackground=active_button_bg, borderwidth=2, variable=crf_value)
        slider.pack(pady=10, padx=20, fill=tk.X)
        
        set_button = tk.Button(crf_window, text="Set", command=set_crf,
                              bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                              activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        set_button.pack(pady=10)
        
        crf_window.wait_window()
        
        return crf_value.get()


class PresetDialog:
    """Dialog for encoding preset selection."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332'
    ) -> str:
        """Show preset selection dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            
        Returns:
            Preset name as string
        """
        preset_window = tk.Toplevel(root)
        preset_window.configure(bg=window_bg)
        preset_window.title("Video Preset")
        preset_window.grab_set()
        
        selected_preset = [DEFAULT_PRESET]
        
        def set_preset(preset: str):
            selected_preset[0] = preset
            preset_window.destroy()
        
        label = tk.Label(preset_window, text="Video Preset", bg=window_bg, fg="white", 
                        font=("Arial", "16", "bold"))
        label.pack(pady=10)
        
        # Create buttons for common presets
        common_presets = ["superfast", "fast", "medium", "slow", "veryslow"]
        for preset in common_presets:
            btn = tk.Button(preset_window, text=preset, command=lambda p=preset: set_preset(p),
                           bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=active_button_bg, activeforeground="white", borderwidth=2)
            btn.pack(pady=2)
        
        preset_window.wait_window()
        
        return selected_preset[0]


class EncodingSettingsDialog:
    """Combined dialog for encoding settings (orientation, resolution, CRF, preset)."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332'
    ) -> Tuple[bool, str, str, str, str, str]:
        """Show encoding settings dialog (replaces get_ratio).
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            
        Returns:
            Tuple of (is_vertical, orientation, width, height, crf, preset)
            - is_vertical: bool - True for vertical, False for horizontal
            - orientation: str - "_horizontal" or "_vertical"
            - width: str - Output width
            - height: str - Output height
            - crf: str - CRF value
            - preset: str - Encoding preset
        """
        settings_window = tk.Toplevel(root)
        settings_window.configure(bg=window_bg)
        settings_window.title("Encoding Settings")
        settings_window.grab_set()
        
        # Default values
        orientation = ["_horizontal"]  # Use list to allow modification in nested functions
        is_vertical = [False]
        width = [str(HD_WIDTH)]
        height = [str(HD_HEIGHT)]
        crf_value = [str(DEFAULT_CRF)]
        preset_value = [DEFAULT_PRESET]
        dialog_completed = [False]
        
        def set_horizontal():
            """Set horizontal orientation and get settings."""
            orientation[0] = "_horizontal"
            is_vertical[0] = False
            
            # Get resolution
            res_width, res_height = ResolutionDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            width[0] = res_width
            height[0] = res_height
            
            # Get CRF
            crf_value[0] = CRFDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            
            # Get preset
            preset_value[0] = PresetDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            
            dialog_completed[0] = True
            settings_window.destroy()
        
        def set_vertical():
            """Set vertical orientation and get settings."""
            orientation[0] = "_vertical"
            is_vertical[0] = True
            
            # Get resolution
            res_width, res_height = ResolutionDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            width[0] = res_width
            height[0] = res_height
            
            # Get CRF
            crf_value[0] = CRFDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            
            # Get preset
            preset_value[0] = PresetDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            
            dialog_completed[0] = True
            settings_window.destroy()
        
        def use_defaults():
            """Use default settings."""
            orientation[0] = "_horizontal"
            is_vertical[0] = False
            width[0] = str(HD_WIDTH)
            height[0] = str(HD_HEIGHT)
            crf_value[0] = str(DEFAULT_CRF)
            preset_value[0] = DEFAULT_PRESET
            dialog_completed[0] = True
            settings_window.destroy()
        
        # Title
        title_label = tk.Label(settings_window, text="Video Encoding Settings", 
                              bg=window_bg, fg="white", font=("Arial", "16", "bold"))
        title_label.pack(pady=10)
        
        # Orientation label
        orientation_label = tk.Label(settings_window, text="Choose Orientation", 
                                    bg=window_bg, fg="white", font=("Arial", "12", "bold"))
        orientation_label.pack(pady=5)
        
        # Orientation buttons frame
        orientation_frame = tk.Frame(settings_window, bg=window_bg)
        orientation_frame.pack(pady=10)
        
        horizontal_button = tk.Button(orientation_frame, text="Horizontal", command=set_horizontal,
                                      bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                                      activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        horizontal_button.pack(side="left", padx=5)
        
        vertical_button = tk.Button(orientation_frame, text="Vertical", command=set_vertical,
                                    bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                                    activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        vertical_button.pack(side="left", padx=5)
        
        # Default settings button
        default_button = tk.Button(settings_window, text="Default Settings", command=use_defaults,
                                  bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                                  activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        default_button.pack(pady=10)
        
        settings_window.wait_window()
        
        # If closed without selection, return defaults
        if not dialog_completed[0]:
            return False, "_horizontal", str(HD_WIDTH), str(HD_HEIGHT), str(DEFAULT_CRF), DEFAULT_PRESET
        
        return is_vertical[0], orientation[0], width[0], height[0], crf_value[0], preset_value[0]


class AudioCodecDialog:
    """Dialog for audio codec selection."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332'
    ) -> str:
        """Show audio codec selection dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            
        Returns:
            Selected audio codec as string
        """
        codec_window = tk.Toplevel(root)
        codec_window.configure(bg=window_bg)
        codec_window.title("Audio Codec")
        codec_window.grab_set()
        
        selected_codec = [DEFAULT_AUDIO_CODEC]
        
        def set_codec(codec: str):
            selected_codec[0] = codec
            codec_window.destroy()
        
        label = tk.Label(codec_window, text="Select Audio Codec", bg=window_bg, fg="white", 
                        font=("Arial", "16", "bold"))
        label.pack(pady=10)
        
        for codec in AUDIO_CODEC_OPTIONS:
            btn = tk.Button(codec_window, text=codec.upper(), command=lambda c=codec: set_codec(c),
                           bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=active_button_bg, activeforeground="white", borderwidth=2)
            btn.pack(pady=2)
        
        codec_window.wait_window()
        return selected_codec[0]


class AudioBitrateDialog:
    """Dialog for audio bitrate selection."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332'
    ) -> str:
        """Show audio bitrate selection dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            
        Returns:
            Selected audio bitrate as string
        """
        bitrate_window = tk.Toplevel(root)
        bitrate_window.configure(bg=window_bg)
        bitrate_window.title("Audio Bitrate")
        bitrate_window.grab_set()
        
        selected_bitrate = [DEFAULT_AUDIO_BITRATE]
        
        def set_bitrate(bitrate: str):
            selected_bitrate[0] = bitrate
            bitrate_window.destroy()
        
        label = tk.Label(bitrate_window, text="Select Audio Bitrate", bg=window_bg, fg="white", 
                        font=("Arial", "16", "bold"))
        label.pack(pady=10)
        
        for bitrate in AUDIO_BITRATE_OPTIONS:
            btn = tk.Button(bitrate_window, text=bitrate, command=lambda b=bitrate: set_bitrate(b),
                           bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=active_button_bg, activeforeground="white", borderwidth=2)
            btn.pack(pady=2)
        
        bitrate_window.wait_window()
        return selected_bitrate[0]


class VideoCodecDialog:
    """Dialog for video codec selection."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332',
        use_gpu: bool = False
    ) -> str:
        """Show video codec selection dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            use_gpu: Whether GPU encoding is being used (affects available codecs)
            
        Returns:
            Selected video codec as string
        """
        codec_window = tk.Toplevel(root)
        codec_window.configure(bg=window_bg)
        codec_window.title("Video Codec")
        codec_window.grab_set()
        
        if use_gpu:
            available_codecs = GPU_CODEC_OPTIONS
            default_codec = GPU_CODEC
        else:
            available_codecs = CPU_CODEC_OPTIONS
            default_codec = CPU_CODEC
        
        selected_codec = [default_codec]
        
        def set_codec(codec: str):
            selected_codec[0] = codec
            codec_window.destroy()
        
        label = tk.Label(codec_window, text="Select Video Codec", bg=window_bg, fg="white", 
                        font=("Arial", "16", "bold"))
        label.pack(pady=10)
        
        codec_descriptions = {
            "libx264": "H.264 (CPU) - Best compatibility",
            "libx265": "H.265/HEVC (CPU) - Better compression",
            "libvpx-vp9": "VP9 (CPU) - Web optimized",
            "h264_nvenc": "H.264 (GPU/NVENC) - Fast encoding",
            "hevc_nvenc": "H.265/HEVC (GPU/NVENC) - Fast + efficient"
        }
        
        for codec in available_codecs:
            description = codec_descriptions.get(codec, codec)
            btn = tk.Button(codec_window, text=f"{codec}\n{description}", 
                           command=lambda c=codec: set_codec(c),
                           bg=button_bg, fg="white", font=("Arial", "9", "bold"),
                           activebackground=active_button_bg, activeforeground="white", borderwidth=2,
                           width=30)
            btn.pack(pady=2)
        
        codec_window.wait_window()
        return selected_codec[0]
