import threading
from datetime import datetime
import time
import tkinter as tk
from threading import Thread
from tkinter import filedialog, messagebox
import subprocess
import os
import re

from VideoScaler import scale_video, get_ratio

WINBOLL = True


def get_total_frames(video_path, output_text, root):
    """Extract video duration and FPS using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration:stream=r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output_lines = result.stdout.strip().splitlines()
        print(len(output_lines))
        if len(output_lines)>3:
            duration_str = output_lines[3]
        else:
            duration_str = output_lines[2]
        fps_str = output_lines[0].split("/")[0]
        return int(int(float(duration_str)) * int(fps_str))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError) as e:
        output_text.insert(tk.END, f"Error: {e}\n")
        return None


def average_list(myList):
    return sum(myList) / len(myList) if myList else 0



def run_scaling(folder_path, output_text, root):
    thread = Thread(target=process_videos_in_folder, args=(folder_path, output_text, root))
    thread.start()


def process_videos_in_folder(folder_path, output_text, root):
    supported_formats = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")
    video_files = [f for f in os.listdir(folder_path) if f.lower().endswith(supported_formats)]
    total_files = len(video_files)

    if not video_files:
        output_text.insert(tk.END, "⚠️ No supported video files found in the folder.\n")
        return

    ratio = get_ratio(root)
    for index, filename in enumerate(video_files, start=1):
        now = datetime.now()
        input_file = os.path.join(folder_path, filename)
        if "_" in filename:
            file_name = filename.split("_")[0]
        elif "mp4" in filename:
            file_name = filename.split(".")[0]
        else:
            file_name = filename
        output_file = os.path.join(folder_path, f"{file_name}_scaled_{now.strftime("%Y%m%d_%H%M%S")}{ratio[1]}.mp4")

        total_frames = get_total_frames(input_file, output_text, root)

        if total_frames:
            output_text.insert(tk.END, f"\n📄 Processing file {index}/{total_files}: {filename}\n")
            output_text.insert(tk.END, f"📁 Output: {output_file}\n")
            output_text.insert(tk.END, f"🎞️ Frames: {total_frames}\n")
            output_text.see(tk.END)

            scale_video(input_file, output_file, total_frames, output_text, root,ratio[0],ratio[2],ratio[3],ratio[4],ratio[5])
        else:
            output_text.insert(tk.END, f"\n⚠️ Running {filename} (frame count error)\n")
            output_text.insert(tk.END, f"\n📄 Processing file {index}/{total_files}: {filename}\n")
            output_text.insert(tk.END, f"📁 Output: {output_file}\n")
            output_text.see(tk.END)

            scale_video(input_file, output_file, total_frames, output_text, root,ratio[0],ratio[2],ratio[3],ratio[4],ratio[5])

    root.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), root.destroy()))




def select_folder(output_text, root):
    global WINBOLL

    root.iconify()
    folder_path = filedialog.askdirectory(title="Select a Folder Containing Videos")
    root.deiconify()

    if folder_path:
        output_text.insert(tk.END, f"📂 Selected folder: {folder_path}\n")
        output_text.see(tk.END)
        run_scaling(folder_path, output_text, root)
    else:
        WINBOLL = False


def main(windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    root = tk.Tk()
    root.configure(bg=windowBg)
    root.title("Folder Video Scaler")
    root.geometry("700x400")
    root.withdraw()

    output_text = tk.Text(root, height=20, width=80, bg=buttonBg, fg="white")
    output_text.pack(padx=10, pady=10)

    select_folder(output_text, root)

    if WINBOLL:
        root.deiconify()
        root.mainloop()
    else:
        root.destroy()


if __name__ == '__main__':
    main()
