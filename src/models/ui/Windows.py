"""
Window classes for Video Editor application.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional
from threading import Thread
from datetime import datetime
import os

from ..VideoInfo import VideoInfo
from ..VideoProcessor import VideoProcessor
from ..VideoJoiner import VideoJoiner
from ..BatchProcessor import BatchProcessor
from ..ConfigManager import get_config_manager
from ..constants import (
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    CANCEL_BUTTON_BG, CANCEL_BUTTON_ACTIVE_BG, CANCELLATION_MESSAGE_DELAY,
    DEFAULT_WINDOW_TITLE, BATCH_WINDOW_TITLE, JOINER_WINDOW_TITLE
)
from .Dialogs import SettingsDialog, ResolutionDialog, CRFDialog, PresetDialog, EncodingSettingsDialog


class VideoScalerWindow:
    """Main window for single video scaling."""
    
    def __init__(
        self,
        window_bg: str = DEFAULT_WINDOW_BG,
        button_bg: str = DEFAULT_BUTTON_BG,
        active_button_bg: str = DEFAULT_ACTIVE_BUTTON_BG
    ):
        """Initialize VideoScalerWindow.
        
        Args:
            window_bg: Window background color
            button_bg: Button background color
            active_button_bg: Active button background color
        """
        self.window_bg = window_bg
        self.button_bg = button_bg
        self.active_button_bg = active_button_bg
        self.processor = VideoProcessor()
        self.video_info = VideoInfo()
        self.config = get_config_manager()
        self.winbool = True
        
        self.window = tk.Tk()
        self.window.configure(bg=window_bg)
        self.window.title(DEFAULT_WINDOW_TITLE)
        self.window.iconify()
        
        # Create main frame for structured layout
        self.main_frame = tk.Frame(self.window, bg=window_bg)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Parameters section (static labels)
        self.params_frame = tk.LabelFrame(self.main_frame, text="Processing Parameters", 
                                         bg=window_bg, fg="white", font=("Arial", "12", "bold"))
        self.params_frame.pack(fill="x", pady=5)
        
        # Progress section (dynamic labels)
        self.progress_frame = tk.LabelFrame(self.main_frame, text="Progress", 
                                           bg=window_bg, fg="white", font=("Arial", "12", "bold"))
        self.progress_frame.pack(fill="x", pady=5)
        
        # Status/Log section (for errors and completion messages)
        self.status_text = tk.Text(self.main_frame, height=5, width=100, bg=button_bg, fg="white")
        self.status_text.pack(fill="both", expand=True, pady=5)
        
        # Cancel button
        self.cancel_button = tk.Button(
            self.window, text="Cancel Operation", command=self.processor.cancel,
            bg=CANCEL_BUTTON_BG, fg="white", font=("Arial", "10", "bold"),
            activebackground=CANCEL_BUTTON_ACTIVE_BG, activeforeground="white", borderwidth=2
        )
        self.cancel_button.pack(pady=5)
        
        # Initialize label references (will be populated when processing starts)
        self.param_labels = {}
        self.progress_labels = {}
        
        self._select_video()
    
    def _select_video(self):
        """Handle video selection and processing."""
        last_input_folder = self.config.get_last_input_folder()
        
        file_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.flv;*.wmv")],
            initialdir=last_input_folder if last_input_folder and os.path.exists(last_input_folder) else None
        )
        
        if file_path:
            self.config.set_last_input_folder(os.path.dirname(file_path))
            
            # Create VideoInfo object to hold video info and user selections
            video_info = VideoInfo(file_path)
            
            # Get performance settings (pass video_info object)
            video_info = SettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, video_info=video_info
            )
            
            # Save settings to config
            self.config.set_performance_settings(video_info.use_gpu, video_info.use_all_cores, video_info.cap_cpu_50)
            if video_info.target_fps is not None:
                self.config.set_target_fps(video_info.target_fps)
            
            # Calculate threads: if cap_cpu_50 is True, use 50% of cores, otherwise use all cores if use_all_cores
            if video_info.cap_cpu_50:
                threads = max(1, video_info.cpu_cores // 2)  # Cap at 50%, minimum 1 thread
            else:
                threads = video_info.cpu_cores if video_info.use_all_cores else 0
            
            # Get encoding settings using new dialog class (pass video_info object)
            video_info = EncodingSettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, video_info=video_info
            )
            
            now = datetime.now()
            
            # Ask for output folder
            last_output_folder = self.config.get_last_output_folder()
            output_folder = filedialog.askdirectory(
                title="Select Output Folder (or Cancel to use same folder as input)",
                initialdir=last_output_folder if last_output_folder and os.path.exists(last_output_folder) else os.path.dirname(file_path)
            )
            
            if output_folder:
                self.config.set_last_output_folder(output_folder)
                input_filename = os.path.splitext(os.path.basename(file_path))[0]
                output_path = os.path.join(
                    output_folder,
                    f"{input_filename.split('_')[0]}_{video_info.orientation}_{video_info.crf}_{video_info.preset}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
                )
            else:
                output_path = os.path.splitext(file_path)[0]
                output_path = f"{output_path.split('_')[0]}_{video_info.orientation}_{video_info.crf}_{video_info.preset}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            total_frames = video_info.get_total_frames()
            
            # Get and display input file size
            input_size = None
            if os.path.exists(file_path):
                try:
                    input_size = os.path.getsize(file_path)
                except Exception:
                    pass
            
            # Clear previous labels if any
            for widget in self.params_frame.winfo_children():
                widget.destroy()
            for widget in self.progress_frame.winfo_children():
                widget.destroy()
            self.param_labels = {}
            self.progress_labels = {}
            
            # Display settings as static labels
            encoding_type = "GPU (NVENC)" if video_info.use_gpu else "CPU"
            if video_info.cap_cpu_50:
                threading_info = f"CPU capped at 50% ({threads} threads)"
            elif video_info.use_all_cores:
                threading_info = f"All cores ({video_info.cpu_cores} threads)"
            else:
                threading_info = "Default (auto)"
            
            fps_info = f"{video_info.target_fps:.2f} fps" if video_info.target_fps is not None else "Keep current"
            
            # Create parameter labels in a grid
            params = [
                ("Encoding Type:", encoding_type),
                ("Threading:", threading_info),
                ("Target FPS:", fps_info),
                ("Input File:", os.path.basename(file_path)),
                ("Output File:", os.path.basename(output_path)),
            ]
            
            if input_size is not None:
                from ..VideoProcessor import VideoProcessor
                params.append(("Input Size:", VideoProcessor.format_file_size(input_size)))
            
            if total_frames:
                params.append(("Total Frames:", str(total_frames)))
            
            for i, (label_text, value_text) in enumerate(params):
                label = tk.Label(self.params_frame, text=label_text, bg=self.window_bg, fg="white", 
                               font=("Arial", "10", "bold"), anchor="w")
                label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
                
                value_label = tk.Label(self.params_frame, text=value_text, bg=self.window_bg, fg="#4CAF50", 
                                     font=("Arial", "10"), anchor="w")
                value_label.grid(row=i, column=1, sticky="w", padx=5, pady=2)
                self.param_labels[label_text] = value_label
            
            # Create progress labels
            progress_items = [
                ("Frames Processed:", "0"),
                ("Progress:", "0.00%"),
                ("Average Frame Rate:", "0"),
                ("Time Running:", "0.00 min"),
                ("Time Remaining:", "00:00:00"),
            ]
            
            for i, (label_text, initial_value) in enumerate(progress_items):
                label = tk.Label(self.progress_frame, text=label_text, bg=self.window_bg, fg="white", 
                               font=("Arial", "10", "bold"), anchor="w")
                label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
                
                value_label = tk.Label(self.progress_frame, text=initial_value, bg=self.window_bg, fg="#FFD700", 
                                     font=("Arial", "10", "bold"), anchor="w")
                value_label.grid(row=i, column=1, sticky="w", padx=5, pady=2)
                self.progress_labels[label_text] = value_label
            
            if not total_frames:
                self.status_text.insert("end", "Could not determine total frames. Progress won't be displayed.\n")
                self.status_text.see("end")
            
            # Process video in background thread to keep UI responsive
            # Use values from video_info object, pass progress labels instead of text widget
            if video_info.use_gpu:
                Thread(target=self.processor.scale_video_gpu, args=(
                    file_path, output_path, total_frames, self.progress_labels, self.status_text, self.window,
                    video_info.is_vertical, str(video_info.target_width), str(video_info.target_height),
                    video_info.crf, video_info.preset, video_info.target_fps
                )).start()
            else:
                Thread(target=self.processor.scale_video_cpu, args=(
                    file_path, output_path, total_frames, self.progress_labels, self.status_text, self.window,
                    video_info.is_vertical, str(video_info.target_width), str(video_info.target_height),
                    video_info.crf, video_info.preset, threads, video_info.target_fps
                )).start()
        else:
            self.winbool = False
    
    def run(self):
        """Run the window mainloop."""
        if self.winbool:
            self.window.deiconify()
            self.window.mainloop()
        else:
            self.window.destroy()


class BatchWindow:
    """Window for batch video processing."""
    
    def __init__(
        self,
        window_bg: str = DEFAULT_WINDOW_BG,
        button_bg: str = DEFAULT_BUTTON_BG,
        active_button_bg: str = DEFAULT_ACTIVE_BUTTON_BG
    ):
        """Initialize BatchWindow."""
        self.window_bg = window_bg
        self.button_bg = button_bg
        self.active_button_bg = active_button_bg
        self.batch_processor = BatchProcessor()
        self.config = get_config_manager()
        self.winbool = True
        
        self.window = tk.Tk()
        self.window.configure(bg=window_bg)
        self.window.title(BATCH_WINDOW_TITLE)
        self.window.geometry("800x600")
        self.window.iconify()
        
        # Create main frame for structured layout
        self.main_frame = tk.Frame(self.window, bg=window_bg)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Parameters section (static labels)
        self.params_frame = tk.LabelFrame(self.main_frame, text="Batch Processing Parameters", 
                                         bg=window_bg, fg="white", font=("Arial", "12", "bold"))
        self.params_frame.pack(fill="x", pady=5)
        
        # Progress section (dynamic labels)
        self.progress_frame = tk.LabelFrame(self.main_frame, text="Batch Progress", 
                                           bg=window_bg, fg="white", font=("Arial", "12", "bold"))
        self.progress_frame.pack(fill="x", pady=5)
        
        # Status/Log section (for file-level messages and errors)
        self.status_text = tk.Text(self.main_frame, height=5, width=100, bg=button_bg, fg="white")
        self.status_text.pack(fill="both", expand=True, pady=5)
        
        # Cancel button
        self.cancel_button = tk.Button(
            self.window, text="Cancel Operation", command=lambda: self.batch_processor.cancel(),
            bg=CANCEL_BUTTON_BG, fg="white", font=("Arial", "10", "bold"),
            activebackground=CANCEL_BUTTON_ACTIVE_BG, activeforeground="white", borderwidth=2
        )
        self.cancel_button.pack(pady=5)
        
        # Initialize label references (will be populated when processing starts)
        self.param_labels = {}
        self.progress_labels = {}
        
        self._select_folder()
    
    def _select_folder(self):
        """Handle folder selection and batch processing."""
        last_input_folder = self.config.get_last_input_folder()
        
        self.window.iconify()
        folder_path = filedialog.askdirectory(
            title="Select a Folder Containing Videos",
            initialdir=last_input_folder if last_input_folder and os.path.exists(last_input_folder) else None
        )
        self.window.deiconify()
        
        if folder_path:
            self.config.set_last_input_folder(folder_path)
            
            # Get first video file to show FPS/size info (if available)
            from ..constants import SUPPORTED_VIDEO_FORMATS
            video_files = [f for f in os.listdir(folder_path) 
                          if f.lower().endswith(SUPPORTED_VIDEO_FORMATS)]
            first_video_path = None
            if video_files:
                first_video_path = os.path.join(folder_path, video_files[0])
            
            # Create VideoInfo object for batch processing (use first video for defaults)
            video_info = VideoInfo(first_video_path) if first_video_path else VideoInfo()
            
            # Get performance settings (pass video_info object)
            video_info = SettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, 
                video_info=video_info
            )
            
            # Save settings to config
            self.config.set_performance_settings(video_info.use_gpu, video_info.use_all_cores, video_info.cap_cpu_50)
            if video_info.target_fps is not None:
                self.config.set_target_fps(video_info.target_fps)
            
            # Calculate threads: if cap_cpu_50 is True, use 50% of cores, otherwise use all cores if use_all_cores
            if video_info.cap_cpu_50:
                threads = max(1, video_info.cpu_cores // 2)  # Cap at 50%, minimum 1 thread
            else:
                threads = video_info.cpu_cores if video_info.use_all_cores else 0
            
            # Get output folder
            last_output_folder = self.config.get_last_output_folder()
            self.window.iconify()
            output_folder = filedialog.askdirectory(
                title="Select Output Folder (or Cancel to use same folder as input)",
                initialdir=last_output_folder if last_output_folder and os.path.exists(last_output_folder) else folder_path
            )
            self.window.deiconify()
            
            if output_folder:
                self.config.set_last_output_folder(output_folder)
            
            # Get encoding settings using new dialog class (pass video_info object)
            video_info = EncodingSettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, video_info=video_info
            )
            
            # Clear previous labels if any
            for widget in self.params_frame.winfo_children():
                widget.destroy()
            for widget in self.progress_frame.winfo_children():
                widget.destroy()
            self.param_labels = {}
            self.progress_labels = {}
            
            # Display settings as static labels (similar to single video window)
            encoding_type = "GPU (NVENC)" if video_info.use_gpu else "CPU"
            if video_info.cap_cpu_50:
                threading_info = f"CPU capped at 50% ({threads} threads)"
            elif video_info.use_all_cores:
                threading_info = f"All cores ({video_info.cpu_cores} threads)"
            else:
                threading_info = "Default (auto)"
            
            fps_info = f"{video_info.target_fps:.2f} fps" if video_info.target_fps is not None else "Keep current"
            resolution_info = f"{video_info.target_width}x{video_info.target_height}"
            
            # Create parameter labels in a grid
            params = [
                ("Encoding Type:", encoding_type),
                ("Threading:", threading_info),
                ("Target FPS:", fps_info),
                ("Resolution:", resolution_info),
                ("CRF:", video_info.crf),
                ("Preset:", video_info.preset),
                ("Input Folder:", os.path.basename(folder_path)),
            ]
            
            if output_folder:
                params.append(("Output Folder:", os.path.basename(output_folder)))
            else:
                params.append(("Output Folder:", "Same as input"))
            
            for i, (label_text, value_text) in enumerate(params):
                label = tk.Label(self.params_frame, text=label_text, bg=self.window_bg, fg="white", 
                               font=("Arial", "10", "bold"), anchor="w")
                label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
                
                value_label = tk.Label(self.params_frame, text=value_text, bg=self.window_bg, fg="#4CAF50", 
                                     font=("Arial", "10"), anchor="w")
                value_label.grid(row=i, column=1, sticky="w", padx=5, pady=2)
                self.param_labels[label_text] = value_label
            
            # Create progress labels (batch-level and per-file progress)
            progress_items = [
                ("Total Files:", "0"),
                ("Files Processed:", "0"),
                ("Overall Progress:", "0.00%"),
                ("Current File:", "-"),
                ("Frames Processed:", "0"),
                ("Progress:", "0.00%"),
                ("Average Frame Rate:", "0"),
                ("Time Running:", "0.00 min"),
                ("Time Remaining:", "00:00:00"),
            ]
            
            for i, (label_text, initial_value) in enumerate(progress_items):
                label = tk.Label(self.progress_frame, text=label_text, bg=self.window_bg, fg="white", 
                               font=("Arial", "10", "bold"), anchor="w")
                label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
                
                value_label = tk.Label(self.progress_frame, text=initial_value, bg=self.window_bg, fg="#FFD700", 
                                     font=("Arial", "10", "bold"), anchor="w")
                value_label.grid(row=i, column=1, sticky="w", padx=5, pady=2)
                self.progress_labels[label_text] = value_label
            
            # Process videos - pass progress labels and status text
            Thread(target=self.batch_processor.process_videos_in_folder, args=(
                folder_path, self.progress_labels, self.status_text, self.window, video_info.use_gpu, threads, output_folder,
                video_info.is_vertical, str(video_info.target_width), str(video_info.target_height),
                video_info.crf, video_info.preset, video_info.target_fps
            )).start()
        else:
            self.winbool = False
    
    def run(self):
        """Run the window mainloop."""
        if self.winbool:
            self.window.deiconify()
            self.window.mainloop()
        else:
            self.window.destroy()


class JoinWindow:
    """Window for joining videos."""
    
    def __init__(
        self,
        window_bg: str = DEFAULT_WINDOW_BG,
        button_bg: str = DEFAULT_BUTTON_BG,
        active_button_bg: str = DEFAULT_ACTIVE_BUTTON_BG
    ):
        """Initialize JoinWindow."""
        self.window_bg = window_bg
        self.button_bg = button_bg
        self.active_button_bg = active_button_bg
        self.joiner = VideoJoiner()
        self.video_info = VideoInfo()
        self.config = get_config_manager()
        self.winbool = True
        
        self.window = tk.Tk()
        self.window.configure(bg=window_bg)
        self.window.title(JOINER_WINDOW_TITLE)
        self.window.iconify()
        
        self.output_text = tk.Text(self.window, height=20, width=80, bg=button_bg, fg="white")
        self.output_text.pack(pady=10)
        
        # Cancel button
        self.cancel_button = tk.Button(
            self.window, text="❌ Cancel Operation", command=self.joiner.cancel,
            bg=CANCEL_BUTTON_BG, fg="white", font=("Arial", "10", "bold"),
            activebackground=CANCEL_BUTTON_ACTIVE_BG, activeforeground="white", borderwidth=2
        )
        self.cancel_button.pack(pady=5)
        
        self._select_folder()
    
    def _select_folder(self):
        """Handle folder selection and video joining."""
        last_join_input_folder = self.config.get_last_join_input_folder()
        
        self.window.iconify()
        folder_path = filedialog.askdirectory(
            title="Select a Folder Containing Videos",
            initialdir=last_join_input_folder if last_join_input_folder and os.path.exists(last_join_input_folder) else None
        )
        self.window.deiconify()
        
        if folder_path:
            self.config.set_last_join_input_folder(folder_path)
            
            # Get output folder
            last_join_output_folder = self.config.get_last_join_output_folder()
            self.window.iconify()
            output_folder = filedialog.askdirectory(
                title="Select Output Folder (or Cancel to use same folder as input)",
                initialdir=last_join_output_folder if last_join_output_folder and os.path.exists(last_join_output_folder) else folder_path
            )
            self.window.deiconify()
            
            if output_folder:
                self.config.set_last_join_output_folder(output_folder)
            
            self.output_text.insert("end", f"Selected folder: {folder_path}\n")
            if output_folder:
                self.output_text.insert("end", f"Output folder: {output_folder}\n")
            else:
                self.output_text.insert("end", f"Output folder: Same as input\n")
            self.output_text.see("end")
            
            Thread(target=self._process_folder, args=(folder_path, output_folder)).start()
        else:
            self.winbool = False
    
    def _process_folder(self, folder_path: str, output_folder: Optional[str]):
        """Process folder for video joining."""
        video_files = self.joiner.get_video_files(folder_path)
        total_files = len(video_files)
        
        if total_files < 2:
            self.output_text.insert("end", "Need at least two compatible videos to join.\n")
            return
        
        self.output_text.insert("end", f"\nFound {total_files} video files to join.\n")
        self.output_text.see("end")
        
        # Check compatibility
        if not self.video_info.check_compatibility(video_files):
            self.output_text.insert("end", "Videos have different properties and can't be joined.\n")
            messagebox.showerror("Incompatible Videos", "Videos have different properties and can't be joined.")
            return
        
        # Create concat file
        concat_file = self.joiner.create_concat_file(video_files, folder_path)
        
        # Determine output file
        from ..constants import JOINED_OUTPUT_FILENAME
        if output_folder:
            output_file = os.path.join(output_folder, JOINED_OUTPUT_FILENAME).replace("\\", "/")
        else:
            output_file = os.path.join(folder_path, JOINED_OUTPUT_FILENAME).replace("\\", "/")
        
        # Join videos
        self.joiner.join_videos(concat_file, output_file, total_files, self.output_text, self.window)
    
    def run(self):
        """Run the window mainloop."""
        if self.winbool:
            self.window.deiconify()
            self.window.mainloop()
        else:
            self.window.destroy()

