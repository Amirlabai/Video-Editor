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
        
        # Initialize settings
        self.use_gpu = tk.BooleanVar(value=default_use_gpu)
        self.use_all_cores = tk.BooleanVar(value=default_use_all_cores)
        self.cap_cpu_50 = tk.BooleanVar(value=False)
        self.target_fps = tk.StringVar(value="")
        self.target_width = tk.StringVar(value=str(FHD_WIDTH))
        self.target_height = tk.StringVar(value=str(FHD_HEIGHT))
        self.crf = tk.StringVar(value=default_crf)
        self.preset = tk.StringVar(value=default_preset)
        self.output_folder = tk.StringVar(value="")
        
        # Create window
        self.window = tk.Tk()
        self.window.configure(bg=window_bg)
        self.window.title("Video Processor")
        self.window.geometry("1200x800")
        
        self._create_ui()
        self._check_gpu_availability()
    
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
        
        # Left panel - Settings
        left_frame = tk.Frame(main_paned, bg=self.window_bg)
        main_paned.add(left_frame, width=400, minsize=350)
        
        # Right panel - Video table
        right_frame = tk.Frame(main_paned, bg=self.window_bg)
        main_paned.add(right_frame, width=800, minsize=600)
        
        self._create_settings_panel(left_frame)
        self._create_video_table(right_frame)
        
        # Bottom buttons
        button_frame = tk.Frame(self.window, bg=self.window_bg)
        button_frame.pack(fill="x", padx=10, pady=5)
        
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
        self.progress_frame = tk.LabelFrame(self.window, text="Progress", 
                                           bg=self.window_bg, fg="white", font=("Arial", "12", "bold"))
        self.progress_frame.pack(fill="x", padx=10, pady=5)
        self.progress_labels = {}
        self._create_progress_labels()
        
        # Status text
        self.status_text = tk.Text(self.window, height=4, width=100, bg=self.button_bg, fg="white")
        self.status_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Action buttons
        action_frame = tk.Frame(self.window, bg=self.window_bg)
        action_frame.pack(fill="x", padx=10, pady=5)
        
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
    
    def _create_settings_panel(self, parent):
        """Create the settings panel on the left."""
        # Scrollable frame for settings
        canvas = tk.Canvas(parent, bg=self.window_bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.window_bg)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Performance Settings
        perf_frame = tk.LabelFrame(scrollable_frame, text="Performance Settings", 
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
        video_frame = tk.LabelFrame(scrollable_frame, text="Video Settings", 
                                    bg=self.window_bg, fg="white", font=("Arial", "11", "bold"))
        video_frame.pack(fill="x", padx=5, pady=5)
        
        # FPS
        fps_frame = tk.Frame(video_frame, bg=self.window_bg)
        fps_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(fps_frame, text="Target FPS (leave empty to keep current):", 
                bg=self.window_bg, fg="white", font=("Arial", "9")).pack(anchor="w")
        fps_entry = tk.Entry(fps_frame, textvariable=self.target_fps, bg=self.button_bg, fg="white")
        fps_entry.pack(fill="x", pady=2)
        
        # Resolution
        res_frame = tk.Frame(video_frame, bg=self.window_bg)
        res_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(res_frame, text="Resolution:", bg=self.window_bg, fg="white", 
                font=("Arial", "9")).pack(anchor="w")
        
        res_buttons_frame = tk.Frame(res_frame, bg=self.window_bg)
        res_buttons_frame.pack(fill="x", pady=2)
        
        def set_resolution(width, height):
            self.target_width.set(str(width))
            self.target_height.set(str(height))
        
        tk.Button(res_buttons_frame, text="HD (1280x720)", 
                 command=lambda: set_resolution(HD_WIDTH, HD_HEIGHT),
                 bg=self.button_bg, fg="white", font=("Arial", "8"),
                 activebackground=self.active_button_bg).pack(side="left", padx=2)
        tk.Button(res_buttons_frame, text="FHD (1920x1080)", 
                 command=lambda: set_resolution(FHD_WIDTH, FHD_HEIGHT),
                 bg=self.button_bg, fg="white", font=("Arial", "8"),
                 activebackground=self.active_button_bg).pack(side="left", padx=2)
        tk.Button(res_buttons_frame, text="4K (3840x2160)", 
                 command=lambda: set_resolution(UHD_4K_WIDTH, UHD_4K_HEIGHT),
                 bg=self.button_bg, fg="white", font=("Arial", "8"),
                 activebackground=self.active_button_bg).pack(side="left", padx=2)
        
        # Custom resolution
        custom_res_frame = tk.Frame(video_frame, bg=self.window_bg)
        custom_res_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(custom_res_frame, text="Custom Resolution:", 
                bg=self.window_bg, fg="white", font=("Arial", "9")).pack(anchor="w")
        res_input_frame = tk.Frame(custom_res_frame, bg=self.window_bg)
        res_input_frame.pack(fill="x", pady=2)
        tk.Entry(res_input_frame, textvariable=self.target_width, width=8, 
                bg=self.button_bg, fg="white").pack(side="left", padx=2)
        tk.Label(res_input_frame, text="x", bg=self.window_bg, fg="white").pack(side="left")
        tk.Entry(res_input_frame, textvariable=self.target_height, width=8, 
                bg=self.button_bg, fg="white").pack(side="left", padx=2)
        
        # Encoding Settings
        encoding_frame = tk.LabelFrame(scrollable_frame, text="Encoding Settings", 
                                      bg=self.window_bg, fg="white", font=("Arial", "11", "bold"))
        encoding_frame.pack(fill="x", padx=5, pady=5)
        
        # CRF
        crf_frame = tk.Frame(encoding_frame, bg=self.window_bg)
        crf_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(crf_frame, text=f"CRF ({CRF_MIN}-{CRF_MAX}, lower=better quality):", 
                bg=self.window_bg, fg="white", font=("Arial", "9")).pack(anchor="w")
        crf_entry = tk.Entry(crf_frame, textvariable=self.crf, bg=self.button_bg, fg="white")
        crf_entry.pack(fill="x", pady=2)
        
        # Preset
        preset_frame = tk.Frame(encoding_frame, bg=self.window_bg)
        preset_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(preset_frame, text="Preset:", bg=self.window_bg, fg="white", 
                font=("Arial", "9")).pack(anchor="w")
        preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset, 
                                    values=PRESET_OPTIONS, state="readonly")
        preset_combo.pack(fill="x", pady=2)
        
        # Output Settings
        output_frame = tk.LabelFrame(scrollable_frame, text="Output Settings", 
                                    bg=self.window_bg, fg="white", font=("Arial", "11", "bold"))
        output_frame.pack(fill="x", padx=5, pady=5)
        
        output_path_frame = tk.Frame(output_frame, bg=self.window_bg)
        output_path_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(output_path_frame, text="Output Folder (leave empty to use input folder):", 
                bg=self.window_bg, fg="white", font=("Arial", "9")).pack(anchor="w")
        output_entry = tk.Entry(output_path_frame, textvariable=self.output_folder, 
                               bg=self.button_bg, fg="white")
        output_entry.pack(fill="x", pady=2, side="left", expand=True)
        tk.Button(output_path_frame, text="Browse", command=self._browse_output_folder,
                 bg=self.button_bg, fg="white", font=("Arial", "8"),
                 activebackground=self.active_button_bg).pack(side="left", padx=2)
    
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
            width = int(self.target_width.get())
            height = int(self.target_height.get())
            crf_val = int(self.crf.get())
            if not (CRF_MIN <= crf_val <= CRF_MAX):
                raise ValueError(f"CRF must be between {CRF_MIN} and {CRF_MAX}")
        except ValueError as e:
            messagebox.showerror("Invalid Settings", f"Please check your settings:\n{str(e)}")
            return
        
        # Get FPS
        target_fps = None
        if self.target_fps.get().strip():
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
    
    def run(self):
        """Run the window mainloop."""
        self.window.mainloop()

