import sys
import tkinter as tk
from pickle import GLOBAL
from tkinter import filedialog, messagebox
import subprocess
import os
import re
import time
from threading import Thread

WINBOLL = True

def get_total_frames(video_path):
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
        duration_str = output_lines[2]
        fps_str = output_lines[0].split("/")[0]
        return int(int(float(duration_str)) * int(fps_str))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError) as e:
        print(f"Error: {e}")
        return None


def average_list(myList):
    tot = sum(myList)
    return tot / len(myList) if myList else 0


def scale_video(input_file, output_file, total_frames, output_text, root):
    ffmpeg_cmd = [
        "ffmpeg", "-i", input_file,
        "-vf", "scale=1280:720",
        "-c:v", "libx264", "-crf", "28", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-progress", "pipe:1", "-nostats",
        output_file
    ]

    try:
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

        output_text.insert(tk.END, "🚀 Starting FFmpeg...\n")
        output_text.see(tk.END)

        # Placeholder for progress line
        progress_line_index = output_text.index(tk.END)
        output_text.insert(tk.END, f"🟢 {input_file} Starting...\n")
        output_text.see(tk.END)

        start_time = time.perf_counter()
        prev_frames = 0
        avg_frame_diff = [0] * 10
        avg_time_diff = [0] * 10
        i = 0

        for line in process.stdout:
            match = re.search(r"frame=\s*(\d+)", line)
            if match:
                frames = int(match.group(1))
                if total_frames:
                    frame_diff = frames - prev_frames
                    now = time.perf_counter()
                    elapsed = now - start_time
                    avg_frame_diff[i] = frame_diff
                    avg_time_diff[i] = elapsed
                    try:
                        remaining_time = ((total_frames - frames) / (
                                    average_list(avg_frame_diff) / average_list(avg_time_diff)))
                    except ZeroDivisionError:
                        remaining_time = 0
                    remaining_time = int(remaining_time)
                    hours, minutes = divmod(remaining_time, 3600)
                    minutes, seconds = divmod(minutes, 60)
                    percent = (frames / total_frames) * 100
                    progress_message = f"🟢 Progress: {frames}/{total_frames} frames ({percent:.2f}%) - Remaining: {hours:02}:{minutes:02}:{seconds:02}"

                    output_text.delete(progress_line_index, f"{progress_line_index} lineend")
                    output_text.insert(progress_line_index, progress_message)
                    output_text.see(tk.END)

                    prev_frames = frames
                    start_time = now
                    i = (i + 1) % 10

        process.wait()

        root.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), root.destroy()))

    except FileNotFoundError:
        messagebox.showerror("Error", "FFmpeg not found! Make sure it's installed and added to PATH.")


def run_scaling(input_file, output_file, total_frames, output_text, window):
    """Runs the scaling in a separate thread."""
    thread = Thread(target=scale_video, args=(input_file, output_file, total_frames, output_text, window))
    thread.start()


def select_video(output_text, window):
    global WINBOLL

    """Opens file dialog and starts video scaling."""
    file_path = filedialog.askopenfilename(
        title="Select a Video File",
        filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.flv;*.wmv")]
    )
    if file_path:
        output_path = os.path.splitext(file_path)[0] + "_scaled.mp4"
        total_frames = get_total_frames(file_path)
        if total_frames:
            output_text.insert(tk.END, f"📂 Selected file: {file_path}\n")
            output_text.insert(tk.END, f"📁 Output file: {output_path}\n")
            output_text.insert(tk.END, f"🎞️ Total frames: {total_frames}\n")
            run_scaling(file_path, output_path, total_frames, output_text, window)
        else:
            output_text.insert(tk.END, "⚠️ Could not determine total frames. Progress will be estimated.\n")
        output_text.see(tk.END)
    else:
        WINBOLL = False


def main(windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    """Creates the Tkinter window."""
    window = tk.Tk()
    window.configure(bg=windowBg)
    window.title("Video Scaler")
    window.iconify()

    output_text = tk.Text(window, height=20, width=80, bg=buttonBg, fg="white")
    output_text.pack()

    select_video(output_text, window)

    if WINBOLL:
        window.deiconify()
        window.mainloop()
    else:
        window.destroy()


if __name__ == '__main__':
    main()