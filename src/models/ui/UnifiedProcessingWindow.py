"""
Unified Processing Window for single and batch video processing.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
from typing import List, Optional, Dict
from threading import Thread
from datetime import datetime
import os
import multiprocessing
import subprocess

from ..VideoInfo import VideoInfo
from ..VideoProcessor import VideoProcessor
from ..ConfigManager import get_config_manager
from ..constants import (
    CANCEL_BUTTON_BG, CANCEL_BUTTON_ACTIVE_BG,
    SUPPORTED_VIDEO_FORMATS, HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT,
    UHD_4K_WIDTH, UHD_4K_HEIGHT, PRESET_OPTIONS,
    CRF_MIN, CRF_MAX
)

ctk.set_default_color_theme("assets/custom-theme.json")

class UnifiedProcessingWindow:
    """Unified window for batch video processing with all options."""
    def __init__(
        self,
        root: ctk.CTk,
    ):
        """Initialize UnifiedProcessingWindow.
        
        Args:
            root: Root window
        """
        self.FPS_OPTIONS = ["12", "24", "25", "29.97", "30", "50", "60", "120"]
        self.RESOLUTION_OPTIONS = ["HD (1280x720)", "FHD (1920x1080)", "4K (3840x2160)"]
        self.processor = VideoProcessor()
        self.config = get_config_manager()
        self.videos: List[VideoInfo] = []  # List of VideoInfo instances
        self.processing = False
        self._current_file_index: Optional[int] = None  # Currently processing file index
        self._pending_callbacks: List[str] = []  # Track pending after() callbacks
        self._is_destroying = False  # Flag to prevent callbacks after destruction
        
        self.cpu_cores = multiprocessing.cpu_count()
        
        # Store default values for reset functionality (lowest settings)
        self.default_fps = self.FPS_OPTIONS[0]
        self.default_resolution = self.RESOLUTION_OPTIONS[0]  # HD (1280x720) - lowest
        self.default_width = HD_WIDTH
        self.default_height = HD_HEIGHT
        self.default_crf = str(CRF_MAX)  # Highest CRF = lowest quality
        self.default_preset = "ultrafast"  # Fastest preset
        self.default_use_gpu = False
        self.default_use_all_cores = False
        
        # Load encoding settings from config
        saved_crf, saved_preset, saved_resolution = self.config.get_encoding_settings()
        
        # Initialize settings (load from config if available, otherwise use defaults)
        self.use_gpu = tk.BooleanVar(value=self.default_use_gpu)
        self.use_all_cores = tk.BooleanVar(value=self.default_use_all_cores)
        self.cap_cpu_50 = tk.BooleanVar(value=False)
        
        # Load FPS from config if available
        saved_fps = self.config.get_target_fps()
        if saved_fps is not None:
            # Find closest FPS option
            closest_fps = min(self.FPS_OPTIONS, key=lambda x: abs(float(x) - saved_fps))
            self.target_fps = tk.StringVar(value=closest_fps)
        else:
            self.target_fps = tk.StringVar(value=self.default_fps)
        
        # Load resolution from config
        resolution_map = {"HD": self.RESOLUTION_OPTIONS[0], "FHD": self.RESOLUTION_OPTIONS[1], "4K": self.RESOLUTION_OPTIONS[2]}
        initial_resolution = resolution_map.get(saved_resolution, self.RESOLUTION_OPTIONS[1])  # Default to FHD
        self.resolution = tk.StringVar(value=initial_resolution)
        
        # Set width/height based on resolution
        if initial_resolution == self.RESOLUTION_OPTIONS[0]:  # HD
            initial_width, initial_height = HD_WIDTH, HD_HEIGHT
        elif initial_resolution == self.RESOLUTION_OPTIONS[1]:  # FHD
            initial_width, initial_height = FHD_WIDTH, FHD_HEIGHT
        else:  # 4K
            initial_width, initial_height = UHD_4K_WIDTH, UHD_4K_HEIGHT
        
        self.target_width = tk.StringVar(value=str(initial_width))
        self.target_height = tk.StringVar(value=str(initial_height))
        
        # Load CRF and preset from config
        self.crf = tk.StringVar(value=saved_crf if saved_crf else self.default_crf)
        self.preset = tk.StringVar(value=saved_preset if saved_preset else self.default_preset)
        # Load last output folder from config
        last_output_folder = self.config.get_last_output_folder()
        self.output_folder = tk.StringVar(value=last_output_folder if last_output_folder else "")
        # Create window
        self.window = ctk.CTkToplevel(root)
        self.window.title("Video Processor")
        self.window.state('zoomed')
        # Ensure cleanup when window is closed
        self.window.protocol("WM_DELETE_WINDOW", self._exit_window)
        
        self._create_ui()
        self._check_gpu_availability()
        # Initialize resolution values based on default selection
        self._update_resolution_from_combo()

        self.running = True
    
    def _check_gpu_availability(self):
        """Check if GPU is available."""
        try:
            cmd = ["ffmpeg", "-hide_banner", "-encoders"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            gpu_available = "h264_nvenc" in result.stdout
            if not gpu_available:
                self.use_gpu.set(False)
                self.gpu_checkbox.configure(state="disabled")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, Exception):
            self.use_gpu.set(False)
            self.gpu_checkbox.configure(state="disabled")
    
    def _create_ui(self):
        """Create the UI layout."""
        # Main container with paned window for resizable panels
        # Use tk.PanedWindow as customtkinter doesn't have equivalent
        main_paned = tk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - Settings (fill vertically)
        left_frame = ctk.CTkFrame(main_paned)
        main_paned.add(left_frame, width=400, minsize=350)
        
        # Right panel - Video table, progress, buttons, status
        right_frame = ctk.CTkFrame(main_paned)
        main_paned.add(right_frame, width=800, minsize=600)
        
        self._create_settings_panel(left_frame)
        self._create_right_panel(right_frame)
    
    def _create_settings_panel(self, parent):
        """Create the settings panel on the left."""
        # Settings frame
        settings_frame = ctk.CTkFrame(parent)
        settings_frame.pack(fill="both", expand=True)
        
        # Performance Settings
        perf_frame = ctk.CTkFrame(settings_frame)
        perf_frame.pack(fill="x", padx=5, pady=5)
        perf_label = ctk.CTkLabel(perf_frame, text="Performance Settings", 
                                  font=ctk.CTkFont(size=18, weight="bold"))
        perf_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # GPU option
        self.gpu_checkbox = ctk.CTkCheckBox(
            perf_frame, text="Use GPU encoding (NVENC)", variable=self.use_gpu,
        )
        self.gpu_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # Threading option
        threading_checkbox = ctk.CTkCheckBox(
            perf_frame, text=f"Use all CPU cores ({self.cpu_cores} threads)", 
            variable=self.use_all_cores,
        )
        threading_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # CPU cap option
        cpu_cap_checkbox = ctk.CTkCheckBox(
            perf_frame, text="Cap CPU usage at 50%", variable=self.cap_cpu_50,
        )
        cpu_cap_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # Video Settings
        video_frame = ctk.CTkFrame(settings_frame)
        video_frame.pack(fill="x", padx=5, pady=5)
        video_label = ctk.CTkLabel(video_frame, text="Video Settings", 
                                   font=ctk.CTkFont(size=18, weight="bold"))
        video_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # FPS
        fps_frame = ctk.CTkFrame(video_frame)
        fps_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(fps_frame, text="Target FPS:").pack(anchor="w")
        self.fps_combo = ctk.CTkComboBox(fps_frame, values=self.FPS_OPTIONS,
                                         variable=self.target_fps,
                                         command=self._on_fps_change,
                                         state="readonly")
        self.fps_combo.pack(fill="x", pady=2)
        # Set initial value
        try:
            initial_index = self.FPS_OPTIONS.index(self.target_fps.get())
            self.fps_combo.set(self.FPS_OPTIONS[initial_index])
        except ValueError:
            self.fps_combo.set(self.FPS_OPTIONS[0])
        
        # Resolution
        res_frame = ctk.CTkFrame(video_frame)
        res_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(res_frame, text="Resolution:").pack(anchor="w")
        
        self.resolution_combo = ctk.CTkComboBox(res_frame, values=self.RESOLUTION_OPTIONS,
                                                variable=self.resolution,
                                                command=self._on_resolution_change,
                                                state="readonly")
        self.resolution_combo.pack(fill="x", pady=2)
        # Set initial value
        try:
            initial_index = self.RESOLUTION_OPTIONS.index(self.resolution.get())
            self.resolution_combo.set(self.RESOLUTION_OPTIONS[initial_index])
        except ValueError:
            self.resolution_combo.set(self.RESOLUTION_OPTIONS[0])
        
        # Encoding Settings
        encoding_frame = ctk.CTkFrame(settings_frame)
        encoding_frame.pack(fill="x", padx=5, pady=5)
        encoding_label = ctk.CTkLabel(encoding_frame, text="Encoding Settings", 
                                      font=ctk.CTkFont(size=18, weight="bold"))
        encoding_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # CRF
        crf_frame = ctk.CTkFrame(encoding_frame)
        crf_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(crf_frame, text=f"CRF ({CRF_MIN}-{CRF_MAX}, lower=better quality):").pack(anchor="w")
        crf_values = [str(i) for i in range(CRF_MIN, CRF_MAX + 1)]
        self.crf_combo = ctk.CTkComboBox(crf_frame, values=crf_values,
                                         variable=self.crf,
                                         command=self._on_crf_change,
                                         state="readonly")
        self.crf_combo.pack(fill="x", pady=2)
        # Set initial value
        try:
            initial_index = crf_values.index(self.crf.get())
            self.crf_combo.set(crf_values[initial_index])
        except ValueError:
            self.crf_combo.set(crf_values[-1])  # Default to last value (30)
        
        # Preset
        preset_frame = ctk.CTkFrame(encoding_frame)
        preset_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(preset_frame, text="Preset:").pack(anchor="w")
        self.preset_combo = ctk.CTkComboBox(preset_frame, values=PRESET_OPTIONS,
                                           variable=self.preset,
                                           command=self._on_preset_change,
                                           state="readonly")
        self.preset_combo.pack(fill="x", pady=2)
        # Set initial value
        try:
            initial_index = PRESET_OPTIONS.index(self.preset.get())
            self.preset_combo.set(PRESET_OPTIONS[initial_index])
        except ValueError:
            self.preset_combo.set(PRESET_OPTIONS[0])  # Default to first value
        
        # Output Settings
        output_frame = ctk.CTkFrame(settings_frame)
        output_frame.pack(fill="x", padx=5, pady=5)
        output_label = ctk.CTkLabel(output_frame, text="Output Settings", 
                                    font=ctk.CTkFont(size=18, weight="bold"))
        output_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        output_path_frame = ctk.CTkFrame(output_frame)
        output_path_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(output_path_frame, text="Output Folder (leave empty to use input folder):").pack(anchor="w")
        output_path_container = ctk.CTkFrame(output_path_frame)
        output_path_container.pack(fill="x", pady=2)
        
        # Create label for displaying output folder (read-only)
        folder_value = self.output_folder.get()
        display_text = self._turncate_folder_name(folder_value) if folder_value else "(empty - will use input folder)"
        self.output_folder_label = ctk.CTkLabel(output_path_container, 
                                               text=display_text,
                                               font=ctk.CTkFont(size=11),
                                               anchor="w")
        self.output_folder_label.pack(side="left", padx=5)
        ctk.CTkButton(output_path_container, text="Browse", command=self._browse_output_folder,width=80).pack(side="right", padx=2)
        
        # Reset to Defaults Button
        reset_frame = ctk.CTkFrame(settings_frame)
        reset_frame.pack(fill="x", padx=5, pady=10)
        ctk.CTkButton(reset_frame, text="Reset to Default Settings", command=self._reset_to_defaults,
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=5)
    
    def _create_right_panel(self, parent):
        """Create the right panel with video table, progress, buttons, and status."""
        # Video table
        self._create_video_table(parent)
        
        # Bottom buttons
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        self.add_files_btn = ctk.CTkButton(
            button_frame, text="Add Files", command=self._add_files,
            font=ctk.CTkFont(weight="bold")
        )
        self.add_files_btn.pack(side="left", padx=5)
        
        self.add_folder_btn = ctk.CTkButton(
            button_frame, text="Add Folder", command=self._add_folder,
            font=ctk.CTkFont(weight="bold")
        )
        self.add_folder_btn.pack(side="left", padx=5)
        
        self.remove_btn = ctk.CTkButton(
            button_frame, text="Remove Selected", command=self._remove_selected,
            font=ctk.CTkFont(weight="bold")
        )
        self.remove_btn.pack(side="left", padx=5)
        
        # Progress section
        self.progress_frame = ctk.CTkFrame(parent)
        self.progress_frame.pack(fill="x", padx=5, pady=5)
        progress_label = ctk.CTkLabel(self.progress_frame, text="Progress", 
                                     font=ctk.CTkFont(size=18, weight="bold"))
        progress_label.pack(anchor="w", padx=5, pady=(5, 0))
        # Create a separate frame for grid layout
        self.progress_grid_frame = ctk.CTkFrame(self.progress_frame)
        self.progress_grid_frame.pack(fill="x", padx=5, pady=5)
        self.progress_labels = {}
        self._create_progress_labels()
        
        # Status text
        self.status_text = ctk.CTkTextbox(parent, height=100)
        self.status_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Action buttons
        action_frame = ctk.CTkFrame(parent)
        action_frame.pack(fill="x", padx=5, pady=5)
        
        self.run_btn = ctk.CTkButton(
            action_frame, text="▶ Run", command=self._run_processing,
            fg_color="#4CAF50", hover_color="#45a049",
            font=ctk.CTkFont(weight="bold")
        )
        self.run_btn.pack(side="left", padx=5)
        
        self.cancel_btn = ctk.CTkButton(
            action_frame, text="❌ Cancel", command=self._cancel_processing,
            fg_color=CANCEL_BUTTON_BG, hover_color=CANCEL_BUTTON_ACTIVE_BG,
            font=ctk.CTkFont(weight="bold")
        )
        self.cancel_btn.pack(side="left", padx=5)
        
        self.exit_btn = ctk.CTkButton(
            action_frame, text="Exit", command=self._exit_window,
            font=ctk.CTkFont(weight="bold")
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
    
    def _on_crf_change(self, value=None):
        """Handle CRF combo box change."""
        # CTkComboBox passes value directly to command
        if value:
            self.crf.set(value)
        else:
            # Fallback: get from combo box
            selected_value = self.crf_combo.get()
            if selected_value:
                self.crf.set(selected_value)
    
    def _on_fps_change(self, value=None):
        """Handle FPS combo box change."""
        # CTkComboBox passes value directly to command
        if value:
            self.target_fps.set(value)
        else:
            # Fallback: get from combo box
            selected_value = self.fps_combo.get()
            if selected_value:
                self.target_fps.set(selected_value)
    
    def _on_preset_change(self, value=None):
        """Handle Preset combo box change."""
        # CTkComboBox passes value directly to command
        if value:
            self.preset.set(value)
        else:
            # Fallback: get from combo box
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
        
        # Update combo box values using .set() for CTkComboBox
        try:
            self.fps_combo.set(self.target_fps.get())
        except ValueError:
            self.fps_combo.set(self.FPS_OPTIONS[0])
        
        try:
            self.resolution_combo.set(self.resolution.get())
        except ValueError:
            self.resolution_combo.set(self.RESOLUTION_OPTIONS[0])
        
        crf_values = [str(i) for i in range(CRF_MIN, CRF_MAX + 1)]
        try:
            self.crf_combo.set(self.crf.get())
        except ValueError:
            self.crf_combo.set(crf_values[-1])
        
        try:
            self.preset_combo.set(self.preset.get())
        except ValueError:
            self.preset_combo.set(PRESET_OPTIONS[0])
        
        self._on_resolution_change()
    
    def _update_fps_from_video(self, video_info: VideoInfo):
        """Update FPS combo box based on video info."""
        # Update FPS if available
        if video_info.fps is not None and hasattr(self, 'fps_combo') and self.fps_combo:
            closest_fps = self._find_closest_fps(video_info.fps)
            # Verify closest_fps is in the options
            if closest_fps in self.FPS_OPTIONS:
                try:
                    # Set StringVar first
                    self.target_fps.set(closest_fps)
                    # Update CTkComboBox using .set()
                    self.fps_combo.set(closest_fps)
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
                # Set StringVar and CTkComboBox
                self.resolution.set(resolution_str)
                self.resolution_combo.set(resolution_str)
            except (ValueError, AttributeError):
                # Fallback: just set the StringVar
                try:
                    self.resolution.set(resolution_str)
                    self.resolution_combo.set(resolution_str)
                except:
                    pass
            self._on_resolution_change()
    
    def _create_video_table(self, parent):
        """Create the video table on the right."""
        table_frame = ctk.CTkFrame(parent)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Table with scrollbar - Keep using ttk.Treeview as customtkinter doesn't have equivalent
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
            
            label = ctk.CTkLabel(self.progress_grid_frame, text=label_text, 
                               font=ctk.CTkFont(weight="bold"), anchor="w")
            label.grid(row=row, column=col, sticky="w", padx=5, pady=2)
            
            value_label = ctk.CTkLabel(self.progress_grid_frame, text=initial_value, 
                                      text_color="#FFD700",
                                      font=ctk.CTkFont(weight="bold"), anchor="w")
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
            # Initialize status to Pending
            video_info.status_done = "Pending"
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
                video_info.status_done
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
        # Get indices in reverse order to avoid index shifting issues
        indices = sorted([self.video_tree.index(item) for item in selected], reverse=True)
        for index in indices:
            if 0 <= index < len(self.videos):
                self.videos.pop(index)
        # Delete tree items
        for item in selected:
            self.video_tree.delete(item)
    
    def _browse_output_folder(self):
        """Browse for output folder."""
        last_output_folder = self.config.get_last_output_folder()
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=last_output_folder if last_output_folder and os.path.exists(last_output_folder) else None
        )
        if folder:
            display_text = self._turncate_folder_name(folder)
            self.config.set_last_output_folder(folder)
            self.output_folder.set(folder)
            self.output_folder_label.configure(text=display_text)

    def _turncate_folder_name(self, folder_name: str) -> str:
        max_chars = 50  # Maximum characters to display
        if len(folder_name) > max_chars:
            return "..." + folder_name[-(max_chars-3):]
        else:
            return folder_name
    
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
            if video_info.is_vertical:
                video_info.target_width = height
                video_info.target_height = width
            else:
                video_info.target_width = width
                video_info.target_height = height
            video_info.crf = self.crf.get()
            video_info.preset = self.preset.get()
            video_info.is_vertical = height > width
        
        # Save settings to config
        self.config.set_performance_settings(
            self.use_gpu.get(), 
            self.use_all_cores.get(), 
            self.cap_cpu_50.get()
        )
        if target_fps:
            self.config.set_target_fps(target_fps)
        
        # Save encoding settings (CRF, preset, resolution)
        resolution_selected = self.resolution.get()
        # Map resolution combo box value to config format
        if resolution_selected == self.RESOLUTION_OPTIONS[0]:  # HD
            resolution_str = "HD"
        elif resolution_selected == self.RESOLUTION_OPTIONS[1]:  # FHD
            resolution_str = "FHD"
        elif resolution_selected == self.RESOLUTION_OPTIONS[2]:  # 4K
            resolution_str = "4K"
        else:
            resolution_str = "FHD"  # Default
        
        self.config.set_encoding_settings(
            self.crf.get(),
            self.preset.get(),
            resolution_str
        )
        
        # Start processing
        self.processing = True
        self.run_btn.configure(state="disabled")
        
        # Process files from queue one by one
        Thread(target=self._process_queue, args=(threads,)).start()
    
    def _process_queue(self, threads: int):
        """Process videos from queue one by one."""
        # Count only pending files (skip completed ones)
        pending_files = [v for v in self.videos if v.status_done == "Pending"]
        total_files = len(pending_files)
        completed_files = sum(1 for v in self.videos if v.status_done == "Completed")
        
        if total_files == 0:
            self._safe_after(0, lambda: messagebox.showinfo("No Files to Process", "All files are already completed."))
            self.processing = False
            self._safe_after(0, lambda: self.run_btn.configure(state="normal"))
            return
        
        self._safe_after(0, lambda: self.progress_labels["Total Files:"].configure(text=str(total_files + completed_files)))
        self._safe_after(0, lambda c=completed_files: self.progress_labels["Files Processed:"].configure(text=f"{c}/{total_files + completed_files}"))
        
        # Process each file in the queue
        for index, video_info in enumerate(self.videos):
            if self.processor._cancel_requested:
                break
            
            # Skip files that are already completed
            if video_info.status_done == "Completed":
                continue
            
            # Only process files that are Pending
            if video_info.status_done != "Pending":
                continue
            
            self._current_file_index = index
            
            # Update status to Processing
            video_info.status_done = "Processing"
            self._safe_after(0, lambda idx=index: self._update_video_status(idx, "Processing"))
            self._safe_after(0, lambda name=os.path.basename(video_info.video_path): 
                           self.progress_labels["Current File:"].configure(text=name))
            
            # Determine output path
            input_file = video_info.video_path
            output_folder = self.output_folder.get().strip() or os.path.dirname(input_file)
            if not os.path.exists(output_folder):
                os.makedirs(output_folder, exist_ok=True)
            
            # Generate output filename
            now = datetime.now()
            input_filename = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(
                output_folder,
                f"{input_filename.split('_')[0]}_{video_info.orientation}_{video_info.crf}_{video_info.preset}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            
            # Get total frames for progress tracking
            total_frames = video_info.get_total_frames()
            
            # Process the video
            try:
                # Get duration and fps from VideoInfo to avoid reloading
                input_duration = video_info.get_duration()
                input_fps = video_info.fps
                
                if video_info.use_gpu:
                    self.processor.scale_video_gpu(
                        input_file, output_file, total_frames, self.progress_labels,
                        self.status_text, self.window, False, str(video_info.target_width),
                        str(video_info.target_height), video_info.crf, video_info.preset,
                        video_info.target_fps, close_window=False,
                        input_duration=input_duration, input_fps=input_fps
                    )
                else:
                    self.processor.scale_video_cpu(
                        input_file, output_file, total_frames, self.progress_labels,
                        self.status_text, self.window, False, str(video_info.target_width),
                        str(video_info.target_height), video_info.crf, video_info.preset,
                        threads, video_info.target_fps, close_window=False,
                        input_duration=input_duration, input_fps=input_fps
                    )
                
                # Update status to Completed if not cancelled
                if not self.processor._cancel_requested:
                    video_info.status_done = "Completed"
                    self._safe_after(0, lambda idx=index: self._update_video_status(idx, "Completed"))
                    # Update progress count
                    completed_count = sum(1 for v in self.videos if v.status_done == "Completed")
                    total_count = len(self.videos)
                    self._safe_after(0, lambda c=completed_count, t=total_count: 
                                   self.progress_labels["Files Processed:"].configure(text=f"{c}/{t}"))
            except Exception as e:
                # Update status to Error
                video_info.status_done = "Error"
                self._safe_after(0, lambda idx=index: self._update_video_status(idx, "Error"))
                self._safe_after(0, lambda msg=str(e), file=os.path.basename(input_file): 
                               self.status_text.insert("end", f"Error processing {file}: {msg}\n"))
        
        # Processing complete
        self.processing = False
        self._current_file_index = None
        self._safe_after(0, lambda: self.run_btn.configure(state="normal"))
        self._safe_after(0, lambda: self.progress_labels["Current File:"].configure(text="-"))
    
    def _update_video_status(self, index: int, status: str):
        """Update video status in table and VideoInfo object."""
        items = self.video_tree.get_children()
        if 0 <= index < len(items) and 0 <= index < len(self.videos):
            item = items[index]
            values = list(self.video_tree.item(item, "values"))
            values[4] = status
            self.video_tree.item(item, values=values)
            # Also update the VideoInfo object
            self.videos[index].status_done = status
    
    def _cancel_processing(self):
        """Cancel processing."""
        self.processor.cancel()
        # Update current file status back to Pending if it was processing
        current_idx = self._current_file_index
        if current_idx is not None and 0 <= current_idx < len(self.videos):
            if self.videos[current_idx].status_done == "Processing":
                self._safe_after(0, lambda idx=current_idx: self._update_video_status(idx, "Pending"))
        self.processing = False
        self._current_file_index = None
        self._safe_after(0, lambda: self.run_btn.configure(state="normal"))
        
    def _safe_after(self, delay_ms: int, callback):
        """Safely schedule a callback with after(), tracking it for cleanup."""
        def safe_callback():
            try:
                # Check if window still exists and we're not destroying
                if not self._is_destroying and self.window.winfo_exists():
                    callback()
            except (tk.TclError, AttributeError):
                # Window was destroyed, ignore
                pass
        
        callback_id = self.window.after(delay_ms, safe_callback)
        self._pending_callbacks.append(callback_id)
        return callback_id
    
    def _cancel_all_callbacks(self):
        """Cancel all pending after() callbacks."""
        self._is_destroying = True
        for callback_id in self._pending_callbacks:
            try:
                self.window.after_cancel(callback_id)
            except (tk.TclError, AttributeError):
                # Window already destroyed or callback already executed
                pass
        self._pending_callbacks.clear()
    
    def _exit_window(self):
        """Close the window."""
        if self.processing:
            if not messagebox.askyesno("Processing in Progress", 
                                       "Processing is in progress. Do you want to cancel and exit?"):
                return
            self._cancel_processing()
        # Cancel all pending callbacks before destroying
        self._cancel_all_callbacks()
        try:
            self.running = False
            self.window.destroy()
        except tk.TclError:
            # Window already destroyed
            pass
    
    def run(self):
        """Run the window mainloop."""
        self.window.mainloop()

    def close(self):
        """Close the window."""
        self._exit_window()