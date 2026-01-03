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
        
        self.output_text = tk.Text(self.window, height=20, width=100, bg=button_bg, fg="white")
        self.output_text.pack(pady=10)
        
        # Cancel button
        self.cancel_button = tk.Button(
            self.window, text="Cancel Operation", command=self.processor.cancel,
            bg=CANCEL_BUTTON_BG, fg="white", font=("Arial", "10", "bold"),
            activebackground=CANCEL_BUTTON_ACTIVE_BG, activeforeground="white", borderwidth=2
        )
        self.cancel_button.pack(pady=5)
        
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
            
            # Get performance settings (pass video path to extract FPS and size)
            use_gpu, use_all_cores, cpu_cores, target_fps, cap_cpu_50 = SettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, video_path=file_path
            )
            
            # Save settings to config
            self.config.set_performance_settings(use_gpu, use_all_cores, cap_cpu_50)
            if target_fps is not None:
                self.config.set_target_fps(target_fps)
            
            # Calculate threads: if cap_cpu_50 is True, use 50% of cores, otherwise use all cores if use_all_cores
            if cap_cpu_50:
                threads = max(1, cpu_cores // 2)  # Cap at 50%, minimum 1 thread
            else:
                threads = cpu_cores if use_all_cores else 0
            
            # Get encoding settings using new dialog class (pass video path for default dimensions)
            ratio = EncodingSettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, video_path=file_path
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
                    f"{input_filename.split('_')[0]}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
                )
            else:
                output_path = os.path.splitext(file_path)[0]
                output_path = f"{output_path.split('_')[0]}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            total_frames = self.video_info.get_total_frames(file_path)
            
            # Get and display input file size
            input_size = None
            if os.path.exists(file_path):
                try:
                    input_size = os.path.getsize(file_path)
                except Exception:
                    pass
            
            # Display settings
            encoding_type = "GPU (NVENC)" if use_gpu else "CPU"
            if cap_cpu_50:
                threading_info = f"CPU capped at 50% ({threads} threads)"
            elif use_all_cores:
                threading_info = f"All cores ({cpu_cores} threads)"
            else:
                threading_info = "Default (auto)"
            
            fps_info = f" | Target FPS: {target_fps:.2f}" if target_fps is not None else " | FPS: Keep current"
            self.output_text.insert("end", f"Encoding: {encoding_type} | Threading: {threading_info}{fps_info}\n")
            
            if total_frames:
                self.output_text.insert("end", f"Selected file: {file_path}\n")
                if input_size is not None:
                    from ..VideoProcessor import VideoProcessor
                    self.output_text.insert("end", f"Input size: {VideoProcessor.format_file_size(input_size)}\n")
                self.output_text.insert("end", f"Output file: {output_path}\n")
                self.output_text.insert("end", f"Total frames: {total_frames}\n")
            else:
                self.output_text.insert("end", "Could not determine total frames. Progress won't be displayed.\n")
                self.output_text.insert("end", f"Selected file: {file_path}\n")
                if input_size is not None:
                    from ..VideoProcessor import VideoProcessor
                    self.output_text.insert("end", f"Input size: {VideoProcessor.format_file_size(input_size)}\n")
                self.output_text.insert("end", f"Output file: {output_path}\n")
            
            # Process video in background thread to keep UI responsive
            if use_gpu:
                Thread(target=self.processor.scale_video_gpu, args=(
                    file_path, output_path, total_frames, self.output_text, self.window,
                    ratio[0], ratio[2], ratio[3], ratio[4], ratio[5], target_fps
                )).start()
            else:
                Thread(target=self.processor.scale_video_cpu, args=(
                    file_path, output_path, total_frames, self.output_text, self.window,
                    ratio[0], ratio[2], ratio[3], ratio[4], ratio[5], threads, target_fps
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
        self.window.geometry("700x400")
        self.window.withdraw()
        
        self.output_text = tk.Text(self.window, height=20, width=120, bg=button_bg, fg="white")
        self.output_text.pack(padx=10, pady=10)
        
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
            
            # Get performance settings (pass first video path if available)
            use_gpu, use_all_cores, cpu_cores, target_fps, cap_cpu_50 = SettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, 
                video_path=first_video_path
            )
            
            # Save settings to config
            self.config.set_performance_settings(use_gpu, use_all_cores, cap_cpu_50)
            if target_fps is not None:
                self.config.set_target_fps(target_fps)
            
            # Calculate threads: if cap_cpu_50 is True, use 50% of cores, otherwise use all cores if use_all_cores
            if cap_cpu_50:
                threads = max(1, cpu_cores // 2)  # Cap at 50%, minimum 1 thread
            else:
                threads = cpu_cores if use_all_cores else 0
            
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
            
            # Get encoding settings using new dialog class (pass first video path for default dimensions)
            ratio = EncodingSettingsDialog.show(
                self.window, self.window_bg, self.button_bg, self.active_button_bg, video_path=first_video_path
            )
            
            # Display settings
            encoding_type = "GPU (NVENC)" if use_gpu else "CPU"
            if cap_cpu_50:
                threading_info = f"CPU capped at 50% ({threads} threads)"
            elif use_all_cores:
                threading_info = f"All cores ({cpu_cores} threads)"
            else:
                threading_info = "Default (auto)"
            
            fps_info = f" | Target FPS: {target_fps:.2f}" if target_fps is not None else " | FPS: Keep current"
            self.output_text.insert("end", f"Encoding: {encoding_type} | Threading: {threading_info}{fps_info}\n")
            self.output_text.insert("end", f"Input folder: {folder_path}\n")
            if output_folder:
                self.output_text.insert("end", f"Output folder: {output_folder}\n")
            else:
                self.output_text.insert("end", f"Output folder: Same as input\n")
            self.output_text.see("end")
            
            # Process videos
            Thread(target=self.batch_processor.process_videos_in_folder, args=(
                folder_path, self.output_text, self.window, use_gpu, threads, output_folder,
                ratio, ratio[2], ratio[3], ratio[4], ratio[5], target_fps
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

