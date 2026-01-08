"""
Window classes for Video Editor application.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional
from threading import Thread
import os

from ..VideoInfo import VideoInfo
from ..VideoJoiner import VideoJoiner
from ..ConfigManager import get_config_manager
from ..constants import (
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    CANCEL_BUTTON_BG, CANCEL_BUTTON_ACTIVE_BG,
    JOINER_WINDOW_TITLE
)

class JoinWindow:
    """Window for joining videos."""
    
    def __init__(
        self,
        root: tk.Tk,
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
        self.running = True
        
        self.window = tk.Toplevel(root)
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
            self.window.protocol("WM_DELETE_WINDOW", self.close)
            self.window.mainloop()
        else:
            self.running = False
            self.window.destroy()

    def close(self):
        """Close the window."""
        self.running = False
        self.window.destroy()

