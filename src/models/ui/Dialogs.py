"""
Dialog classes for Video Editor application.
"""

import tkinter as tk
import subprocess
import multiprocessing
from typing import Tuple, Optional
from ..ConfigManager import get_config_manager
from ..VideoInfo import VideoInfo
from ..constants import (
    HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT, UHD_4K_WIDTH, UHD_4K_HEIGHT,
    CRF_MIN, CRF_MAX, DEFAULT_CRF, DEFAULT_PRESET, PRESET_OPTIONS,
    DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE, AUDIO_CODEC_OPTIONS, AUDIO_BITRATE_OPTIONS,
    CPU_CODEC, CPU_CODEC_OPTIONS, GPU_CODEC, GPU_CODEC_OPTIONS
)


class SettingsDialog:
    """Dialog for performance settings (GPU/CPU, threading, FPS, CPU cap)."""
    
    @staticmethod
    def show(
        root,
        window_bg: str = '#1e1e1e',
        button_bg: str = '#323232',
        active_button_bg: str = '#192332',
        video_info: Optional[VideoInfo] = None
    ) -> VideoInfo:
        """Show performance settings dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            video_info: Optional VideoInfo object (will be modified with user selections)
            
        Returns:
            VideoInfo object with all user selections stored in it
        """
        config = get_config_manager()
        default_use_gpu, default_use_all_cores = config.get_performance_settings()
        
        perf_window = tk.Toplevel(root)
        perf_window.configure(bg=window_bg)
        perf_window.title("Performance Settings")
        perf_window.grab_set()
        perf_window.geometry("500x600")
        
        use_gpu = tk.BooleanVar(perf_window, value=default_use_gpu)
        use_all_cores = tk.BooleanVar(perf_window, value=default_use_all_cores)
        cap_cpu_50 = tk.BooleanVar(perf_window, value=False)
        gpu_available = SettingsDialog._check_gpu_compatibility()
        cpu_cores = multiprocessing.cpu_count()
        
        # Initialize video_info if not provided
        if video_info is None:
            video_info = VideoInfo()
        
        def confirm_settings():
            # Store settings in video_info object
            video_info.use_gpu = use_gpu.get()
            video_info.use_all_cores = use_all_cores.get()
            video_info.cap_cpu_50 = cap_cpu_50.get()
            video_info.cpu_cores = cpu_cores  # Store system CPU count
            
            # Save to config
            config.set_performance_settings(use_gpu.get(), use_all_cores.get(), cap_cpu_50.get())
            if video_info.target_fps is not None:
                config.set_target_fps(video_info.target_fps)
            perf_window.destroy()
        
        row = 0
        
        # Video info display
        if video_info.fps is not None:
            video_info_frame = tk.Frame(perf_window, bg=window_bg, relief=tk.RAISED, borderwidth=2)
            video_info_frame.grid(row=row, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
            
            video_info_label = tk.Label(video_info_frame, text="Video Information", 
                                       bg=window_bg, fg="white", font=("Arial", "12", "bold"))
            video_info_label.pack(pady=5)
            
            fps_label = tk.Label(video_info_frame, text=f"Current FPS: {video_info.fps:.2f}", 
                                bg=window_bg, fg="white", font=("Arial", "10"))
            fps_label.pack(pady=2)
            
            size_label = tk.Label(video_info_frame, text=f"Video Size: {video_info.width}x{video_info.height}", 
                                 bg=window_bg, fg="white", font=("Arial", "10"))
            size_label.pack(pady=2)
            
            row += 1
            
            # FPS reduction options
            fps_frame = tk.Frame(perf_window, bg=window_bg)
            fps_frame.grid(row=row, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
            row += 1
            
            fps_title = tk.Label(fps_frame, text="Frame Rate (FPS) Reduction", 
                                bg=window_bg, fg="white", font=("Arial", "12", "bold"))
            fps_title.pack(pady=5)
            
            fps_desc = tk.Label(fps_frame, text="Select a lower FPS to reduce file size (only reduction allowed)", 
                               bg=window_bg, fg="white", font=("Arial", "9"))
            fps_desc.pack(pady=2)
            
            fps_buttons_frame = tk.Frame(fps_frame, bg=window_bg)
            fps_buttons_frame.pack(pady=5)
            
            # Store buttons for state management
            fps_buttons = []
            
            def set_fps(fps: Optional[float], selected_button: tk.Button):
                video_info.target_fps = fps
                # Update button states - reset all, then highlight selected
                for btn in fps_buttons:
                    btn.config(relief=tk.RAISED)
                selected_button.config(relief=tk.SUNKEN)
            
            # Keep current FPS button
            keep_current_btn = tk.Button(fps_buttons_frame, text=f"Keep Current ({video_info.fps:.2f} fps)", 
                                       command=lambda: set_fps(None, keep_current_btn),
                                       bg=button_bg, fg="white", font=("Arial", "9", "bold"),
                                       activebackground=active_button_bg, activeforeground="white", 
                                       borderwidth=2, relief=tk.SUNKEN)
            keep_current_btn.pack(side="left", padx=2)
            fps_buttons.append(keep_current_btn)
            video_info.target_fps = None  # Default to keep current
            
            # Only show lower FPS options if current FPS is higher
            if video_info.fps > 30:
                fps_30_btn = tk.Button(fps_buttons_frame, text="30 fps", 
                                      command=lambda: set_fps(30.0, fps_30_btn),
                                      bg=button_bg, fg="white", font=("Arial", "9", "bold"),
                                      activebackground=active_button_bg, activeforeground="white", 
                                      borderwidth=2)
                fps_30_btn.pack(side="left", padx=2)
                fps_buttons.append(fps_30_btn)
            
            if video_info.fps > 24:
                fps_24_btn = tk.Button(fps_buttons_frame, text="24 fps", 
                                      command=lambda: set_fps(24.0, fps_24_btn),
                                      bg=button_bg, fg="white", font=("Arial", "9", "bold"),
                                      activebackground=active_button_bg, activeforeground="white", 
                                      borderwidth=2)
                fps_24_btn.pack(side="left", padx=2)
                fps_buttons.append(fps_24_btn)
            
            if video_info.fps > 12:
                fps_12_btn = tk.Button(fps_buttons_frame, text="12 fps", 
                                      command=lambda: set_fps(12.0, fps_12_btn),
                                      bg=button_bg, fg="white", font=("Arial", "9", "bold"),
                                      activebackground=active_button_bg, activeforeground="white", 
                                      borderwidth=2)
                fps_12_btn.pack(side="left", padx=2)
                fps_buttons.append(fps_12_btn)
        
        # GPU option
        if gpu_available:
            gpu_label = tk.Label(perf_window, text="🚀 GPU (NVENC) Available!", 
                                bg=window_bg, fg="#4CAF50", font=("Arial", "12", "bold"))
            gpu_label.grid(row=row, column=0, columnspan=2, pady=10, padx=10)
            row += 1
            
            gpu_checkbox = tk.Checkbutton(perf_window, text="Use GPU encoding (Much Faster!)", 
                                          variable=use_gpu, bg=window_bg, fg="white",
                                          selectcolor=active_button_bg, font=("Arial", "10", "bold"))
            gpu_checkbox.grid(row=row, column=0, columnspan=2, pady=5, padx=10, sticky="w")
            row += 1
        else:
            gpu_label = tk.Label(perf_window, text="⚠️ GPU (NVENC) Not Available", 
                                bg=window_bg, fg="#FF9800", font=("Arial", "12", "bold"))
            gpu_label.grid(row=row, column=0, columnspan=2, pady=10, padx=10)
            row += 1
            
            gpu_info = tk.Label(perf_window, text="Using CPU encoding", bg=window_bg, fg="white", 
                               font=("Arial", "9"))
            gpu_info.grid(row=row, column=0, columnspan=2, pady=5, padx=10)
            row += 1
        
        # Threading option
        threading_label = tk.Label(perf_window, text="CPU Threading", bg=window_bg, fg="white", 
                                  font=("Arial", "12", "bold"))
        threading_label.grid(row=row, column=0, columnspan=2, pady=(20, 5), padx=10)
        row += 1
        
        cores_info = tk.Label(perf_window, text=f"Available CPU cores: {cpu_cores}", 
                             bg=window_bg, fg="white", font=("Arial", "9"))
        cores_info.grid(row=row, column=0, columnspan=2, pady=5, padx=10)
        row += 1
        
        threading_checkbox = tk.Checkbutton(perf_window, 
                                            text=f"Use all CPU cores (Default: FFmpeg auto, All cores: {cpu_cores} threads)", 
                                            variable=use_all_cores, bg=window_bg, fg="white",
                                            selectcolor=active_button_bg, font=("Arial", "10", "bold"))
        threading_checkbox.grid(row=row, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        row += 1
        
        # CPU cap option
        cpu_cap_label = tk.Label(perf_window, text="CPU Usage Limit", bg=window_bg, fg="white", 
                                 font=("Arial", "12", "bold"))
        cpu_cap_label.grid(row=row, column=0, columnspan=2, pady=(20, 5), padx=10)
        row += 1
        
        cpu_cap_checkbox = tk.Checkbutton(perf_window, 
                                          text="Cap CPU usage at 50% (slower but uses less resources)", 
                                          variable=cap_cpu_50, bg=window_bg, fg="white",
                                          selectcolor=active_button_bg, font=("Arial", "10", "bold"))
        cpu_cap_checkbox.grid(row=row, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        row += 1
        
        # Confirm button
        confirm_button = tk.Button(perf_window, text="Confirm", command=confirm_settings, 
                                  bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                                  activebackground=active_button_bg, activeforeground="white", borderwidth=2)
        confirm_button.grid(row=row, column=0, columnspan=2, pady=20, padx=10)
        
        perf_window.wait_window()
        
        # Store CPU cores in object before returning (in case dialog was closed without confirming)
        if video_info.cpu_cores is None:
            video_info.cpu_cores = cpu_cores
        
        return video_info
    
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
        active_button_bg: str = '#192332',
        video_info: Optional[VideoInfo] = None,
        is_vertical: bool = False
    ) -> Tuple[str, str]:
        """Show resolution selection dialog.
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            video_info: Optional VideoInfo object to get default dimensions from
            is_vertical: Whether this is for vertical orientation (will flip dimensions on return)
            
        Returns:
            Tuple of (width, height) as strings
            If is_vertical is True, the dimensions are flipped (height, width)
        """
        res_window = tk.Toplevel(root)
        res_window.configure(bg=window_bg)
        res_window.title("Video Resolution")
        res_window.grab_set()
        
        # Get video dimensions from video_info if provided
        default_width = None
        default_height = None
        if video_info and video_info.width is not None and video_info.height is not None:
            default_width = video_info.width
            default_height = video_info.height
        
        selected_res = [None, None]
        
        def set_original():
            """Use original video dimensions."""
            if default_width and default_height:
                selected_res[0] = str(default_width)
                selected_res[1] = str(default_height)
            else:
                selected_res[0] = str(HD_WIDTH)
                selected_res[1] = str(HD_HEIGHT)
            res_window.destroy()
        
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
        
        # Show "Use Original" button if we have video dimensions
        if default_width and default_height:
            original_button = tk.Button(res_window, text=f"Use Original: {default_width}x{default_height}", 
                                       command=set_original,
                                       bg=button_bg, fg="white", font=("Arial", "10", "bold"),
                                       activebackground=active_button_bg, activeforeground="white", borderwidth=2)
            original_button.pack(pady=5)
        
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
            # Return default dimensions if available, otherwise HD
            if default_width and default_height:
                width, height = str(default_width), str(default_height)
            else:
                width, height = str(HD_WIDTH), str(HD_HEIGHT)
        else:
            width, height = selected_res[0], selected_res[1]
        
        # If vertical orientation, flip width and height on return
        if is_vertical:
            return height, width
        return width, height


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
        active_button_bg: str = '#192332',
        video_info: Optional[VideoInfo] = None
    ) -> VideoInfo:
        """Show encoding settings dialog (replaces get_ratio).
        
        Args:
            root: Parent window
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
            video_info: Optional VideoInfo object (will be modified with user selections)
            
        Returns:
            VideoInfo object with user selections stored in it
        """
        settings_window = tk.Toplevel(root)
        settings_window.configure(bg=window_bg)
        settings_window.title("Encoding Settings")
        settings_window.grab_set()
        
        # Initialize video_info if not provided
        if video_info is None:
            video_info = VideoInfo()
        
        # Use video dimensions as defaults if available
        default_width = video_info.width if video_info.width else HD_WIDTH
        default_height = video_info.height if video_info.height else HD_HEIGHT
        
        dialog_completed = [False]
        
        def set_horizontal():
            """Set horizontal orientation and get settings."""
            video_info.orientation = "_horizontal"
            video_info.is_vertical = False
            
            # Get resolution - pass video_info so dialog can use stored dimensions
            res_width, res_height = ResolutionDialog.show(
                settings_window, window_bg, button_bg, active_button_bg,
                video_info=video_info, is_vertical=False
            )
            video_info.target_width = int(res_width)
            video_info.target_height = int(res_height)
            
            # Get CRF
            crf = CRFDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            video_info.crf = crf
            
            # Get preset
            preset = PresetDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            video_info.preset = preset
            
            dialog_completed[0] = True
            settings_window.destroy()
        
        def set_vertical():
            """Set vertical orientation and get settings."""
            video_info.orientation = "_vertical"
            video_info.is_vertical = True
            
            # Get resolution - pass video_info so dialog can use stored dimensions
            # ResolutionDialog will flip them on return since is_vertical=True
            res_width, res_height = ResolutionDialog.show(
                settings_window, window_bg, button_bg, active_button_bg,
                video_info=video_info, is_vertical=True
            )
            # ResolutionDialog already flipped the dimensions for vertical orientation
            video_info.target_width = int(res_width)
            video_info.target_height = int(res_height)
            
            # Get CRF
            crf = CRFDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            video_info.crf = crf
            
            # Get preset
            preset = PresetDialog.show(
                settings_window, window_bg, button_bg, active_button_bg
            )
            video_info.preset = preset
            
            dialog_completed[0] = True
            settings_window.destroy()
        
        def use_defaults():
            """Use default settings (original video dimensions)."""
            video_info.target_width = default_width
            video_info.target_height = default_height
            video_info.crf = str(DEFAULT_CRF)
            video_info.preset = DEFAULT_PRESET
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
        
        # If closed without selection, set defaults (original video dimensions if available)
        if not dialog_completed[0]:
            use_defaults()
        
        return video_info


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
