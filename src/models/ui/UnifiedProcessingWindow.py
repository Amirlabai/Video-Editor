"""
Unified Processing Window for single and batch video processing.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional, Dict
from threading import Thread
from datetime import datetime
import os
import multiprocessing

from ..VideoInfo import VideoInfo
from ..VideoProcessor import VideoProcessor
from ..BatchProcessor import BatchProcessor
from ..ConfigManager import get_config_manager
from ..constants import (
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    CANCEL_BUTTON_BG, CANCEL_BUTTON_ACTIVE_BG, CANCELLATION_MESSAGE_DELAY,
    SUPPORTED_VIDEO_FORMATS, HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT,
    UHD_4K_WIDTH, UHD_4K_HEIGHT, DEFAULT_CRF, DEFAULT_PRESET, PRESET_OPTIONS,
    CRF_MIN, CRF_MAX
)


class UnifiedProcessingWindow:
    """Unified window for single and batch video processing with all options."""
    
    # Class constants for combo box options
    FPS_OPTIONS = ["12", "24", "25", "29.97", "30", "50", "60", "120"]
    RESOLUTION_OPTIONS = ["HD (1280x720)", "FHD (1920x1080)", "4K (3840x2160)"]
    
    def __init__(
        self,
        window_bg: str = DEFAULT_WINDOW_BG,
        button_bg: str = DEFAULT_BUTTON_BG,
        active_button_bg: str = DEFAULT_ACTIVE_BUTTON_BG
    ):
        """Initialize UnifiedProcessingWindow.
        
        Args:
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
        """
        self.window_bg = window_bg
        self.button_bg = button_bg
        self.active_button_bg = active_button_bg
        self.processor = VideoProcessor()
        self.batch_processor = BatchProcessor()
        self.config = get_config_manager()
        self.videos: List[VideoInfo] = []  # List of VideoInfo instances
        self.processing = False
        
        # Get default settings
        default_use_gpu, default_use_all_cores = self.config.get_performance_settings()
        default_crf, default_preset, default_resolution = self.config.get_encoding_settings()
        self.cpu_cores = multiprocessing.cpu_count()
        
        # Map default_resolution from config format to combo box format
        resolution_map = {
            "HD": "HD (1280x720)",
            "FHD": "FHD (1920x1080)",
            "4K": "4K (3840x2160)"
        }
        default_resolution_combo = resolution_map.get(default_resolution, "HD (1280x720)")
        
        # Set default width/height based on resolution
        if default_resolution == "HD":
            default_width, default_height = HD_WIDTH, HD_HEIGHT
        elif default_resolution == "FHD":
            default_width, default_height = FHD_WIDTH, FHD_HEIGHT
        elif default_resolution == "4K":
            default_width, default_height = UHD_4K_WIDTH, UHD_4K_HEIGHT
        else:
            default_width, default_height = HD_WIDTH, HD_HEIGHT
        
        # Store default values for reset functionality (lowest settings)
        self.default_fps = self.FPS_OPTIONS[0]
        self.default_resolution = self.RESOLUTION_OPTIONS[0]  # HD (1280x720) - lowest
        self.default_width = HD_WIDTH
        self.default_height = HD_HEIGHT
        self.default_crf = str(CRF_MAX)  # Highest CRF = lowest quality
        self.default_preset = "ultrafast"  # Fastest preset
        self.default_use_gpu = False
        self.default_use_all_cores = False
        
        # Initialize settings (use reset defaults for initial display)
        self.use_gpu = tk.BooleanVar(value=self.default_use_gpu)
        self.use_all_cores = tk.BooleanVar(value=self.default_use_all_cores)
        self.cap_cpu_50 = tk.BooleanVar(value=False)
        self.target_fps = tk.StringVar(value=self.default_fps)
        self.resolution = tk.StringVar(value=self.default_resolution)
        self.target_width = tk.StringVar(value=str(self.default_width))
        self.target_height = tk.StringVar(value=str(self.default_height))
        self.crf = tk.StringVar(value=self.default_crf)
        self.preset = tk.StringVar(value=self.default_preset)
        # Load last output folder from config
        last_output_folder = self.config.get_last_output_folder()
        self.output_folder = tk.StringVar(value=last_output_folder if last_output_folder else "")
        
        # Create window
        self.window = tk.Tk()
        self.window.configure(bg=window_bg)
        self.window.title("Video Processor")
        self.window.state('zoomed')
        
        self._create_ui()
        self._check_gpu_availability()
        # Initialize resolution values based on default selection
        self._update_resolution_from_combo()
    
    def _check_gpu_availability(self):
        """Check if GPU is available."""
        try:
            import subprocess
            cmd = ["ffmpeg", "-hide_banner", "-encoders"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            gpu_available = "h264_nvenc" in result.stdout
            if not gpu_available:
                self.use_gpu.set(False)
                self.gpu_checkbox.config(state="disabled")
        except:
            self.use_gpu.set(False)
            self.gpu_checkbox.config(state="disabled")
    
    def _create_ui(self):
        """Create the UI layout."""
        # Main container with paned window for resizable panels
        main_paned = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, bg=self.window_bg)
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - Settings (fill vertically)
        left_frame = tk.Frame(main_paned, bg=self.window_bg)
        main_paned.add(left_frame, width=400, minsize=350)
        
        # Right panel - Video table, progress, buttons, status
        right_frame = tk.Frame(main_paned, bg=self.window_bg)
        main_paned.add(right_frame, width=800, minsize=600)
        
        self._create_settings_panel(left_frame)
        self._create_right_panel(right_frame)
    
    def _create_settings_panel(self, parent):
        """Create the settings panel on the left."""
        # Settings frame
        settings_frame = tk.Frame(parent, bg=self.window_bg)
        settings_frame.pack(fill="both", expand=True)
        
        # Performance Settings
        perf_frame = tk.LabelFrame(settings_frame, text="Performance Settings", 
                                   bg=self.window_bg, fg="white", font=("Arial", "11", "bold"))
        perf_frame.pack(fill="x", padx=5, pady=5)
        
        # GPU option
        self.gpu_checkbox = tk.Checkbutton(
            perf_frame, text="Use GPU encoding (NVENC)", variable=self.use_gpu,
            bg=self.window_bg, fg="white", selectcolor=self.active_button_bg,
            font=("Arial", "10")
        )
        self.gpu_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # Threading option
        threading_checkbox = tk.Checkbutton(
            perf_frame, text=f"Use all CPU cores ({self.cpu_cores} threads)", 
            variable=self.use_all_cores,
            bg=self.window_bg, fg="white", selectcolor=self.active_button_bg,
            font=("Arial", "10")
        )
        threading_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # CPU cap option
        cpu_cap_checkbox = tk.Checkbutton(
            perf_frame, text="Cap CPU usage at 50%", variable=self.cap_cpu_50,
            bg=self.window_bg, fg="white", selectcolor=self.active_button_bg,
            font=("Arial", "10")
        )
        cpu_cap_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # Video Settings
        video_frame = tk.LabelFrame(settings_frame, text="Video Settings", 
                                    bg=self.window_bg, fg="white", font=("Arial", "11", "bold"))
        video_frame.pack(fill="x", padx=5, pady=5)
        
        # FPS
        fps_frame = tk.Frame(video_frame, bg=self.window_bg)
        fps_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(fps_frame, text="Target FPS:", 
                bg=self.window_bg, fg="white", font=("Arial", "9")).pack(anchor="w")
        self.fps_combo = ttk.Combobox(fps_frame, textvariable=self.target_fps, 
                                values=self.FPS_OPTIONS, 
                                state="readonly")
        self.fps_combo.pack(fill="x", pady=2)
        self.fps_combo.bind("<<ComboboxSelected>>", self._on_fps_change)
        # Set initial value by finding index
        try:
            initial_index = self.FPS_OPTIONS.index(self.target_fps.get())
            self.fps_combo.current(initial_index)
        except ValueError:
            self.fps_combo.current(0)  # Default to first value (12)
        
        # Resolution
        res_frame = tk.Frame(video_frame, bg=self.window_bg)
        res_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(res_frame, text="Resolution:", bg=self.window_bg, fg="white", 
                font=("Arial", "9")).pack(anchor="w")
        
        self.resolution_combo = ttk.Combobox(res_frame, textvariable=self.resolution,
                                       values=self.RESOLUTION_OPTIONS,
                                       state="readonly")
        self.resolution_combo.pack(fill="x", pady=2)
        self.resolution_combo.bind("<<ComboboxSelected>>", self._on_resolution_change)
        # Set initial value by finding index
        try:
            initial_index = self.RESOLUTION_OPTIONS.index(self.resolution.get())
            self.resolution_combo.current(initial_index)
        except ValueError:
            self.resolution_combo.current(1)  # Default to FHD
        
        # Encoding Settings
        encoding_frame = tk.LabelFrame(settings_frame, text="Encoding Settings", 
                                      bg=self.window_bg, fg="white", font=("Arial", "11", "bold"))
        encoding_frame.pack(fill="x", padx=5, pady=5)
        
        # CRF
        crf_frame = tk.Frame(encoding_frame, bg=self.window_bg)
        crf_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(crf_frame, text=f"CRF ({CRF_MIN}-{CRF_MAX}, lower=better quality):", 
                bg=self.window_bg, fg="white", font=("Arial", "9")).pack(anchor="w")
        crf_values = [str(i) for i in range(CRF_MIN, CRF_MAX + 1)]
        self.crf_combo = ttk.Combobox(crf_frame, textvariable=self.crf, 
                                values=crf_values, state="readonly")
        self.crf_combo.pack(fill="x", pady=2)
        self.crf_combo.bind("<<ComboboxSelected>>", self._on_crf_change)
        # Set initial value by finding index
        try:
            initial_index = crf_values.index(self.crf.get())
            self.crf_combo.current(initial_index)
        except ValueError:
            self.crf_combo.current(len(crf_values) - 1)  # Default to last value (30)
        
        # Preset
        preset_frame = tk.Frame(encoding_frame, bg=self.window_bg)
        preset_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(preset_frame, text="Preset:", bg=self.window_bg, fg="white", 
                font=("Arial", "9")).pack(anchor="w")
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset, 
                                    values=PRESET_OPTIONS, state="readonly")
        self.preset_combo.pack(fill="x", pady=2)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)
        # Set initial value by finding index
        try:
            initial_index = PRESET_OPTIONS.index(self.preset.get())
            self.preset_combo.current(initial_index)
        except ValueError:
            self.preset_combo.current(0)  # Default to first value
        
        # Output Settings
        output_frame = tk.LabelFrame(settings_frame, text="Output Settings", 
                                    bg=self.window_bg, fg="white", font=("Arial", "11", "bold"))
        output_frame.pack(fill="x", padx=5, pady=5)
        
        output_path_frame = tk.Frame(output_frame, bg=self.window_bg)
        output_path_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(output_path_frame, text="Output Folder (leave empty to use input folder):", 
                bg=self.window_bg, fg="white", font=("Arial", "9")).pack(anchor="w")
        output_path_container = tk.Frame(output_path_frame, bg=self.window_bg)
        output_path_container.pack(fill="x", pady=2)
        # Create label for displaying output folder (read-only)
        folder_value = self.output_folder.get()
        display_text = folder_value if folder_value else "(empty - will use input folder)"
        self.output_folder_label = tk.Label(output_path_container, 
                                           text=display_text,
                                           bg=self.button_bg, fg="white", 
                                           font=("Arial", "9"),
                                           anchor="w", relief="sunken", padx=5, pady=2)
        self.output_folder_label.pack(fill="x", side="left", expand=True)
        tk.Button(output_path_container, text="Browse", command=self._browse_output_folder,
                 bg=self.button_bg, fg="white", font=("Arial", "8"),
                 activebackground=self.active_button_bg).pack(side="left", padx=2)
        
        # Reset to Defaults Button
        reset_frame = tk.Frame(settings_frame, bg=self.window_bg)
        reset_frame.pack(fill="x", padx=5, pady=10)
        tk.Button(reset_frame, text="Reset to Default Settings", command=self._reset_to_defaults,
                 bg=self.button_bg, fg="white", font=("Arial", "10", "bold"),
                 activebackground=self.active_button_bg, activeforeground="white", borderwidth=2).pack(fill="x", padx=5)
    
    def _create_right_panel(self, parent):
        """Create the right panel with video table, progress, buttons, and status."""
        # Video table
        self._create_video_table(parent)
        
        # Bottom buttons
        button_frame = tk.Frame(parent, bg=self.window_bg)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        self.add_files_btn = tk.Button(
            button_frame, text="Add Files", command=self._add_files,
            bg=self.button_bg, fg="white", font=("Arial", "10", "bold"),
            activebackground=self.active_button_bg, activeforeground="white", borderwidth=2
        )
        self.add_files_btn.pack(side="left", padx=5)
        
        self.add_folder_btn = tk.Button(
            button_frame, text="Add Folder", command=self._add_folder,
            bg=self.button_bg, fg="white", font=("Arial", "10", "bold"),
            activebackground=self.active_button_bg, activeforeground="white", borderwidth=2
        )
        self.add_folder_btn.pack(side="left", padx=5)
        
        self.remove_btn = tk.Button(
            button_frame, text="Remove Selected", command=self._remove_selected,
            bg=self.button_bg, fg="white", font=("Arial", "10", "bold"),
            activebackground=self.active_button_bg, activeforeground="white", borderwidth=2
        )
        self.remove_btn.pack(side="left", padx=5)
        
        # Progress section
        self.progress_frame = tk.LabelFrame(parent, text="Progress", 
                                           bg=self.window_bg, fg="white", font=("Arial", "12", "bold"))
        self.progress_frame.pack(fill="x", padx=5, pady=5)
        self.progress_labels = {}
        self._create_progress_labels()
        
        # Status text
        self.status_text = tk.Text(parent, height=4, width=100, bg=self.button_bg, fg="white")
        self.status_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Action buttons
        action_frame = tk.Frame(parent, bg=self.window_bg)
        action_frame.pack(fill="x", padx=5, pady=5)
        
        self.run_btn = tk.Button(
            action_frame, text="▶ Run", command=self._run_processing,
            bg="#4CAF50", fg="white", font=("Arial", "12", "bold"),
            activebackground="#45a049", activeforeground="white", borderwidth=2
        )
        self.run_btn.pack(side="left", padx=5)
        
        self.cancel_btn = tk.Button(
            action_frame, text="❌ Cancel", command=self._cancel_processing,
            bg=CANCEL_BUTTON_BG, fg="white", font=("Arial", "12", "bold"),
            activebackground=CANCEL_BUTTON_ACTIVE_BG, activeforeground="white", borderwidth=2
        )
        self.cancel_btn.pack(side="left", padx=5)
        
        self.exit_btn = tk.Button(
            action_frame, text="Exit", command=self._exit_window,
            bg=self.button_bg, fg="white", font=("Arial", "12", "bold"),
            activebackground=self.active_button_bg, activeforeground="white", borderwidth=2
        )
        self.exit_btn.pack(side="right", padx=5)
    
    def _on_resolution_change(self, event=None):
        """Handle resolution combo box change."""
        selected = self.resolution.get()
        if selected == self.RESOLUTION_OPTIONS[0]:  # HD (1280x720)
            self.target_width.set(str(HD_WIDTH))
            self.target_height.set(str(HD_HEIGHT))
        elif selected == self.RESOLUTION_OPTIONS[1]:  # FHD (1920x1080)
            self.target_width.set(str(FHD_WIDTH))
            self.target_height.set(str(FHD_HEIGHT))
        elif selected == self.RESOLUTION_OPTIONS[2]:  # 4K (3840x2160)
            self.target_width.set(str(UHD_4K_WIDTH))
            self.target_height.set(str(UHD_4K_HEIGHT))
    
    def _on_crf_change(self, event=None):
        """Handle CRF combo box change."""
        # Ensure self.crf is synced with the combo box selection
        selected_value = self.crf_combo.get()
        if selected_value:
            self.crf.set(selected_value)
    
    def _on_fps_change(self, event=None):
        """Handle FPS combo box change."""
        # Ensure self.target_fps is synced with the combo box selection
        selected_value = self.fps_combo.get()
        if selected_value:
            self.target_fps.set(selected_value)
    
    def _on_preset_change(self, event=None):
        """Handle Preset combo box change."""
        # Ensure self.preset is synced with the combo box selection
        selected_value = self.preset_combo.get()
        if selected_value:
            self.preset.set(selected_value)
    
    def _update_resolution_from_combo(self):
        """Update resolution values from combo box selection."""
        self._on_resolution_change()
    
    def _map_resolution_to_combo(self, width: int, height: int) -> str:
        """Map resolution dimensions to combo box format."""
        if width == HD_WIDTH and height == HD_HEIGHT:
            return self.RESOLUTION_OPTIONS[0]  # HD (1280x720)
        elif width == FHD_WIDTH and height == FHD_HEIGHT:
            return self.RESOLUTION_OPTIONS[1]  # FHD (1920x1080)
        elif width == UHD_4K_WIDTH and height == UHD_4K_HEIGHT:
            return self.RESOLUTION_OPTIONS[2]  # 4K (3840x2160)
        else:
            # Return closest match or default
            return self.RESOLUTION_OPTIONS[0]  # HD (1280x720)
    
    def _find_closest_fps(self, fps: float) -> str:
        """Find closest FPS value in combo box options."""
        fps_options = [float(f) for f in self.FPS_OPTIONS]
        closest = min(fps_options, key=lambda x: abs(x - fps))
        if closest == 29.97:
            return "29.97"
        return str(int(closest))
    
    def _reset_to_defaults(self):
        """Reset all settings to default values."""
        # Use stored default values
        self.target_fps.set(self.default_fps)
        self.resolution.set(self.default_resolution)
        self.target_width.set(str(self.default_width))
        self.target_height.set(str(self.default_height))
        self.crf.set(self.default_crf)
        self.preset.set(self.default_preset)
        self.use_gpu.set(self.default_use_gpu)
        self.use_all_cores.set(self.default_use_all_cores)
        self.cap_cpu_50.set(False)
        
        # Update combo box current indices using the values
        try:
            self.fps_combo.current(self.FPS_OPTIONS.index(self.target_fps.get()))
        except ValueError:
            self.fps_combo.current(0)
        
        try:
            self.resolution_combo.current(self.RESOLUTION_OPTIONS.index(self.resolution.get()))
        except ValueError:
            self.resolution_combo.current(0)
        
        crf_values = [str(i) for i in range(CRF_MIN, CRF_MAX + 1)]
        try:
            self.crf_combo.current(crf_values.index(self.crf.get()))
        except ValueError:
            self.crf_combo.current(len(crf_values) - 1)
        
        try:
            self.preset_combo.current(PRESET_OPTIONS.index(self.preset.get()))
        except ValueError:
            self.preset_combo.current(0)
        
        self._on_resolution_change()
    
    def _update_fps_from_video(self, video_info: VideoInfo):
        """Update FPS combo box based on video info."""
        # Update FPS if available
        if video_info.fps is not None and hasattr(self, 'fps_combo') and self.fps_combo:
            closest_fps = self._find_closest_fps(video_info.fps)
            # Verify closest_fps is in the options
            if closest_fps in self.FPS_OPTIONS:
                try:
                    fps_index = self.FPS_OPTIONS.index(closest_fps)
                    # Set StringVar first
                    self.target_fps.set(closest_fps)
                    # Update combobox: change state, set current, set back to readonly
                    self.fps_combo.config(state="normal")
                    self.fps_combo.current(fps_index)
                    # Verify the value was set
                    current_value = self.fps_combo.get()
                    if current_value != closest_fps:
                        # If not set correctly, try setting it directly
                        self.fps_combo.set(closest_fps)
                    self.fps_combo.config(state="readonly")
                    # Double-check StringVar matches
                    if self.target_fps.get() != closest_fps:
                        self.target_fps.set(closest_fps)
                except Exception as e:
                    # Fallback: just set StringVar
                    self.target_fps.set(closest_fps)
    
    def _update_settings_from_video(self, video_info: VideoInfo):
        """Update FPS and resolution combo boxes based on video info."""
        # Update FPS if available
        self._update_fps_from_video(video_info)
        
        # Update resolution if available
        if video_info.width is not None and video_info.height is not None and hasattr(self, 'resolution_combo'):
            resolution_str = self._map_resolution_to_combo(video_info.width, video_info.height)
            try:
                res_index = self.RESOLUTION_OPTIONS.index(resolution_str)
                # Temporarily change state to update value, then set back to readonly
                self.resolution_combo.config(state="normal")
                self.resolution.set(resolution_str)
                self.resolution_combo.current(res_index)
                self.resolution_combo.config(state="readonly")
            except (ValueError, AttributeError):
                # Fallback: just set the StringVar
                try:
                    self.resolution_combo.config(state="normal")
                    self.resolution.set(resolution_str)
                    self.resolution_combo.config(state="readonly")
                except:
                    pass
            self._on_resolution_change()
    
    def _create_video_table(self, parent):
        """Create the video table on the right."""
        table_frame = tk.Frame(parent, bg=self.window_bg)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Table with scrollbar
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.video_tree = ttk.Treeview(
            table_frame,
            columns=("File", "Resolution", "FPS", "Size", "Status"),
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="extended"
        )
        scrollbar.config(command=self.video_tree.yview)
        
        # Configure columns
        self.video_tree.heading("File", text="File Name")
        self.video_tree.heading("Resolution", text="Resolution")
        self.video_tree.heading("FPS", text="FPS")
        self.video_tree.heading("Size", text="Size")
        self.video_tree.heading("Status", text="Status")
        
        self.video_tree.column("File", width=200)
        self.video_tree.column("Resolution", width=120)
        self.video_tree.column("FPS", width=80)
        self.video_tree.column("Size", width=100)
        self.video_tree.column("Status", width=100)
        
        self.video_tree.pack(fill="both", expand=True)
    
    def _create_progress_labels(self):
        """Create progress labels."""
        progress_items = [
            ("Total Files:", "0"),
            ("Files Processed:", "0"),
            ("Current File:", "-"),
            ("Frames Processed:", "0/0"),
            ("Progress:", "0.00%"),
            ("Average Frame Rate:", "0 fps"),
            ("Time Running:", "0.00 min"),
            ("Time Remaining:", "00:00:00"),
        ]
        
        for i, (label_text, initial_value) in enumerate(progress_items):
            row = i // 2
            col = (i % 2) * 2
            
            label = tk.Label(self.progress_frame, text=label_text, bg=self.window_bg, fg="white", 
                           font=("Arial", "9", "bold"), anchor="w")
            label.grid(row=row, column=col, sticky="w", padx=5, pady=2)
            
            value_label = tk.Label(self.progress_frame, text=initial_value, bg=self.window_bg, fg="#FFD700", 
                                 font=("Arial", "9", "bold"), anchor="w")
            value_label.grid(row=row, column=col+1, sticky="w", padx=5, pady=2)
            self.progress_labels[label_text] = value_label
    
    def _add_files(self):
        """Add video files."""
        last_input_folder = self.config.get_last_input_folder()
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.flv;*.wmv")],
            initialdir=last_input_folder if last_input_folder and os.path.exists(last_input_folder) else None
        )
        
        if files:
            self.config.set_last_input_folder(os.path.dirname(files[0]))
            for file_path in files:
                self._add_video(file_path)
    
    def _add_folder(self):
        """Add all videos from a folder."""
        last_input_folder = self.config.get_last_input_folder()
        folder = filedialog.askdirectory(
            title="Select Folder Containing Videos",
            initialdir=last_input_folder if last_input_folder and os.path.exists(last_input_folder) else None
        )
        
        if folder:
            self.config.set_last_input_folder(folder)
            video_files = [f for f in os.listdir(folder) 
                          if f.lower().endswith(SUPPORTED_VIDEO_FORMATS)]
            for video_file in video_files:
                self._add_video(os.path.join(folder, video_file))
    
    def _add_video(self, file_path: str):
        """Add a single video to the list."""
        try:
            video_info = VideoInfo(file_path)
            is_first_video = len(self.videos) == 0
            self.videos.append(video_info)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            size_str = self._format_size(file_size)
            
            # Insert into table
            resolution = f"{video_info.width}x{video_info.height}" if video_info.width and video_info.height else "Unknown"
            fps_str = f"{video_info.fps:.2f}" if video_info.fps else "Unknown"
            
            self.video_tree.insert("", "end", values=(
                os.path.basename(file_path),
                resolution,
                fps_str,
                size_str,
                "Pending"
            ))
            
            # Update FPS from newly added video (always update FPS to match the file)
            self._update_fps_from_video(video_info)
            
            # Update settings (including resolution) from first video added
            if is_first_video:
                # Call directly - UI should be ready by now
                self._update_settings_from_video(video_info)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video {file_path}:\n{str(e)}")
    
    def _remove_selected(self):
        """Remove selected videos from the list."""
        selected = self.video_tree.selection()
        for item in selected:
            index = self.video_tree.index(item)
            if 0 <= index < len(self.videos):
                self.videos.pop(index)
            self.video_tree.delete(item)
    
    def _browse_output_folder(self):
        """Browse for output folder."""
        last_output_folder = self.config.get_last_output_folder()
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=last_output_folder if last_output_folder and os.path.exists(last_output_folder) else None
        )
        if folder:
            self.config.set_last_output_folder(folder)
            self.output_folder.set(folder)
            # Update the display label
            self.output_folder_label.config(text=folder)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _run_processing(self):
        """Run video processing."""
        if not self.videos:
            messagebox.showwarning("No Videos", "Please add videos to process.")
            return
        
        if self.processing:
            messagebox.showwarning("Already Processing", "Processing is already in progress.")
            return
        
        # Validate settings
        try:
            # Parse resolution from combo box
            resolution_selected = self.resolution.get()
            if resolution_selected == self.RESOLUTION_OPTIONS[0]:  # HD (1280x720)
                width = HD_WIDTH
                height = HD_HEIGHT
            elif resolution_selected == self.RESOLUTION_OPTIONS[1]:  # FHD (1920x1080)
                width = FHD_WIDTH
                height = FHD_HEIGHT
            elif resolution_selected == self.RESOLUTION_OPTIONS[2]:  # 4K (3840x2160)
                width = UHD_4K_WIDTH
                height = UHD_4K_HEIGHT
            else:
                raise ValueError("Please select a valid resolution")
            
            crf_val = int(self.crf.get())
            if not (CRF_MIN <= crf_val <= CRF_MAX):
                raise ValueError(f"CRF must be between {CRF_MIN} and {CRF_MAX}")
        except ValueError as e:
            messagebox.showerror("Invalid Settings", f"Please check your settings:\n{str(e)}")
            return
        
        # Get FPS from combo box
        try:
            target_fps = float(self.target_fps.get())
        except ValueError:
            messagebox.showerror("Invalid FPS", "FPS must be a number.")
            return
        
        # Calculate threads
        if self.cap_cpu_50.get():
            threads = max(1, self.cpu_cores // 2)
        else:
            threads = self.cpu_cores if self.use_all_cores.get() else 0
        
        # Update all videos with settings
        for video_info in self.videos:
            video_info.use_gpu = self.use_gpu.get()
            video_info.use_all_cores = self.use_all_cores.get()
            video_info.cap_cpu_50 = self.cap_cpu_50.get()
            video_info.cpu_cores = self.cpu_cores
            video_info.target_fps = target_fps
            video_info.target_width = width
            video_info.target_height = height
            video_info.crf = self.crf.get()
            video_info.preset = self.preset.get()
            video_info.is_vertical = height > width
            video_info.orientation = "_vertical" if video_info.is_vertical else "_horizontal"
        
        # Save settings to config
        self.config.set_performance_settings(
            self.use_gpu.get(), 
            self.use_all_cores.get(), 
            self.cap_cpu_50.get()
        )
        if target_fps:
            self.config.set_target_fps(target_fps)
        
        # Start processing
        self.processing = True
        self.run_btn.config(state="disabled")
        
        # Determine if single file or batch
        if len(self.videos) == 1:
            Thread(target=self._process_single, args=(threads,)).start()
        else:
            Thread(target=self._process_batch, args=(threads,)).start()
    
    def _process_single(self, threads: int):
        """Process a single video."""
        video_info = self.videos[0]
        input_file = video_info.video_path
        
        # Determine output path
        output_folder = self.output_folder.get().strip() or os.path.dirname(input_file)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)
        
        now = datetime.now()
        input_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(
            output_folder,
            f"{input_filename.split('_')[0]}_{video_info.orientation}_{video_info.crf}_{video_info.preset}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        
        total_frames = video_info.get_total_frames()
        
        # Update progress
        self.window.after(0, lambda: self.progress_labels["Total Files:"].config(text="1"))
        self.window.after(0, lambda: self.progress_labels["Current File:"].config(text=os.path.basename(input_file)))
        
        # Process
        if video_info.use_gpu:
            self.processor.scale_video_gpu(
                input_file, output_file, total_frames, self.progress_labels,
                self.status_text, self.window, False, str(video_info.target_width),
                str(video_info.target_height), video_info.crf, video_info.preset,
                video_info.target_fps, close_window=False
            )
        else:
            self.processor.scale_video_cpu(
                input_file, output_file, total_frames, self.progress_labels,
                self.status_text, self.window, False, str(video_info.target_width),
                str(video_info.target_height), video_info.crf, video_info.preset,
                threads, video_info.target_fps, close_window=False
            )
        
        self.processing = False
        self.window.after(0, lambda: self.run_btn.config(state="normal"))
        self.window.after(0, lambda: self._update_video_status(0, "Completed"))
    
    def _process_batch(self, threads: int):
        """Process multiple videos."""
        # Group videos by folder
        folders = {}
        for video_info in self.videos:
            folder = os.path.dirname(video_info.video_path)
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(video_info)
        
        # Process each folder
        total_files = len(self.videos)
        processed = 0
        
        self.window.after(0, lambda: self.progress_labels["Total Files:"].config(text=str(total_files)))
        
        for folder, videos in folders.items():
            output_folder = self.output_folder.get().strip() or folder
            
            # Use first video's settings (they should all be the same after _run_processing)
            video_info = videos[0]
            
            self.batch_processor.process_videos_in_folder(
                folder, self.progress_labels, self.status_text, self.window,
                video_info.use_gpu, threads, output_folder, video_info.is_vertical,
                str(video_info.target_width), str(video_info.target_height),
                video_info.crf, video_info.preset, video_info.target_fps
            )
            
            processed += len(videos)
            self.window.after(0, lambda p=processed: self.progress_labels["Files Processed:"].config(text=str(p)))
        
        self.processing = False
        self.window.after(0, lambda: self.run_btn.config(state="normal"))
    
    def _update_video_status(self, index: int, status: str):
        """Update video status in table."""
        items = self.video_tree.get_children()
        if 0 <= index < len(items):
            item = items[index]
            values = list(self.video_tree.item(item, "values"))
            values[4] = status
            self.video_tree.item(item, values=values)
    
    def _cancel_processing(self):
        """Cancel processing."""
        self.processor.cancel()
        self.batch_processor.cancel()
        self.processing = False
        self.window.after(0, lambda: self.run_btn.config(state="normal"))
    
    def _exit_window(self):
        """Close the window."""
        if self.processing:
            if not messagebox.askyesno("Processing in Progress", 
                                       "Processing is in progress. Do you want to cancel and exit?"):
                return
            self._cancel_processing()
        self.window.destroy()
    
    def run(self):
        """Run the window mainloop."""
        self.window.mainloop()

