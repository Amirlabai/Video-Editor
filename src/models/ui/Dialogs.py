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
    CRF_MIN, CRF_MAX, DEFAULT_CRF, DEFAULT_PRESET, PRESET_OPTIONS
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

