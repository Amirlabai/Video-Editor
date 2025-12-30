import threading
from datetime import datetime
import time
import tkinter as tk
from threading import Thread
from tkinter import filedialog, messagebox
import subprocess
import os
import re
from .constants import SUPPORTED_VIDEO_FORMATS, DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG

try:
    # Try relative import first (when used as a module)
    from .VideoScaler import *
except ImportError:
    # Fallback for absolute import (when running as script or if relative fails)
    from models.VideoScaler import *
WINBOOL = True


def average_list(myList):
    return sum(myList) / len(myList) if myList else 0



def run_scaling(folder_path, output_text, root, use_gpu=False, threads=0, output_folder=None):
    thread = Thread(target=process_videos_in_folder, args=(folder_path, output_text, root, use_gpu, threads, output_folder))
    thread.start()

def run_file(folder_path, output_text, root, index, filename, total_files, ratio, use_gpu=False, threads=0, output_folder=None):
    now = datetime.now()
    input_file = os.path.join(folder_path, filename)
    
    if "mp4" in filename:
        file_name = filename.split(".")[0]
    else:
        file_name = filename
    
    # Use output_folder if provided, otherwise use input folder
    if output_folder:
        output_file = os.path.join(output_folder, f"{file_name}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4")
    else:
        output_file = os.path.join(folder_path, f"{file_name}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4")

    total_frames = get_total_frames(input_file)

    if total_frames:
        output_text.insert(tk.END, f"\n📄 Processing file {index}/{total_files}: {filename}\n")
        output_text.insert(tk.END, f"📁 Output: {output_file}\n")
        output_text.insert(tk.END, f"🎞️ Frames: {total_frames}\n")
        output_text.see(tk.END)

        if use_gpu:
            scale_video_GPU(input_file, output_file, total_frames, output_text, root, ratio[0], ratio[2], ratio[3], ratio[4], ratio[5])
        else:
            scale_video_CPU(input_file, output_file, total_frames, output_text, root, ratio[0], ratio[2], ratio[3], ratio[4], ratio[5], threads=threads)
        
        
    else:
        output_text.insert(tk.END, f"\n⚠️ Running {filename} (frame count error)\n")
        output_text.insert(tk.END, f"\n📄 Processing file {index}/{total_files}: {filename}\n")
        output_text.insert(tk.END, f"📁 Output: {output_file}\n")
        output_text.see(tk.END)

        if use_gpu:
            scale_video_GPU(input_file, output_file, total_frames, output_text, root, ratio[0], ratio[2], ratio[3], ratio[4], ratio[5])
        else:
            scale_video_CPU(input_file, output_file, total_frames, output_text, root, ratio[0], ratio[2], ratio[3], ratio[4], ratio[5], threads=threads)

    output_text.insert(tk.END, f"\n")

def process_videos_in_folder(folder_path, output_text, root, use_gpu=False, threads=0, output_folder=None):
    video_files = [f for f in os.listdir(folder_path) if f.lower().endswith(SUPPORTED_VIDEO_FORMATS)]
    total_files = len(video_files)

    if not video_files:
        output_text.insert(tk.END, "⚠️ No supported video files found in the folder.\n")
        return

    ratio = get_ratio(root)
    for index, filename in enumerate(video_files, start=1):
        run_file(folder_path, output_text, root, index, filename, total_files, ratio, use_gpu, threads, output_folder)

    root.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), root.destroy()))




def select_folder(output_text, root, windowBg='#1e1e1e', buttonBg='#323232', activeButtonBg='#192332'):
    global WINBOOL

    root.iconify()
    folder_path = filedialog.askdirectory(title="Select a Folder Containing Videos")
    root.deiconify()

    if folder_path:
        # Get performance settings
        use_gpu, use_all_cores, cpu_cores = get_performance_settings(root, windowBg, buttonBg, activeButtonBg)
        threads = cpu_cores if use_all_cores else 0
        
        # Ask for output folder
        root.iconify()
        output_folder = filedialog.askdirectory(
            title="Select Output Folder (or Cancel to use same folder as input)",
            initialdir=folder_path
        )
        root.deiconify()
        
        # Display settings info
        encoding_type = "GPU (NVENC)" if use_gpu else "CPU"
        threading_info = f"All cores ({cpu_cores} threads)" if use_all_cores else "Default (auto)"
        output_text.insert(tk.END, f"⚙️ Encoding: {encoding_type} | Threading: {threading_info}\n")
        output_text.insert(tk.END, f"📂 Input folder: {folder_path}\n")
        if output_folder:
            output_text.insert(tk.END, f"📁 Output folder: {output_folder}\n")
        else:
            output_text.insert(tk.END, f"📁 Output folder: Same as input\n")
        output_text.see(tk.END)
        run_scaling(folder_path, output_text, root, use_gpu, threads, output_folder)
    else:
        WINBOOL = False


def main(windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    root = tk.Tk()
    root.configure(bg=windowBg)
    root.title("Folder Video Scaler")
    root.geometry("700x400")
    root.withdraw()

    output_text = tk.Text(root, height=20, width=120, bg=buttonBg, fg="white")
    output_text.pack(padx=10, pady=10)

    select_folder(output_text, root, windowBg, buttonBg, activeButtonBg)

    if WINBOOL:
        root.deiconify()
        root.mainloop()
    else:
        root.destroy()


if __name__ == '__main__':
    main()
