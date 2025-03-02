import time
import tkinter as tk
from threading import Thread
from tkinter import filedialog, messagebox
import subprocess
import os
import re


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
        duration_str = output_lines[2]
        fps_str = output_lines[0].split("/")[0]
        return int(int(float(duration_str)) * int(fps_str))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError) as e:
        output_text.insert(tk.END, f"Error: {e}\n")
        return None


def average_list(myList):
    return sum(myList) / len(myList) if myList else 0


def scale_video(input_file, output_file, total_frames, output_text, root, file_index, total_files):
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
        output_text.insert(tk.END, f"🟢 [{file_index}/{total_files}] Progress: Starting...\n")
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
                    progress_message = f"🟢 [{file_index}/{total_files}] Progress: {frames}/{total_frames} frames ({percent:.2f}%) - Remaining: {hours:02}:{minutes:02}:{seconds:02}"

                    output_text.delete(progress_line_index, f"{progress_line_index} lineend")
                    output_text.insert(progress_line_index, progress_message)
                    output_text.see(tk.END)

                    prev_frames = frames
                    start_time = now
                    i = (i + 1) % 10

        process.wait()

        if process.returncode == 0:
            output_text.insert(tk.END, f"\n✅ Finished: {output_file}\n")
        else:
            output_text.insert(tk.END, "\n❌ FFmpeg failed! Check the logs above.\n")
        output_text.see(tk.END)

    except FileNotFoundError:
        messagebox.showerror("Error", "FFmpeg not found! Make sure it's installed and added to PATH.")


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

    for index, filename in enumerate(video_files, start=1):
        input_file = os.path.join(folder_path, filename)
        output_file = os.path.join(folder_path, f"scaled_{filename}")

        total_frames = get_total_frames(input_file, output_text, root)

        if total_frames:
            output_text.insert(tk.END, f"\n📄 Processing file {index}/{total_files}: {filename}\n")
            output_text.insert(tk.END, f"📁 Output: {output_file}\n")
            output_text.insert(tk.END, f"🎞️ Frames: {total_frames}\n")
            output_text.see(tk.END)

            scale_video(input_file, output_file, total_frames, output_text, root, index, total_files)
        else:
            output_text.insert(tk.END, f"\n⚠️ Skipping {filename} (frame count error)\n")
            output_text.see(tk.END)

    output_text.insert(tk.END, "\n✅ All videos have been processed!\n")
    output_text.see(tk.END)

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
