import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread
import time
import re


WINBOLL = True


def get_video_info(video_path):
    """Extract codec, resolution, and framerate using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        codec, width, height, framerate = result.stdout.strip().splitlines()
        return codec, int(width), int(height), framerate
    except Exception as e:
        return None


def check_compatibility(video_files, output_text):
    """Ensure all videos have matching codec, resolution, and framerate."""
    reference_info = get_video_info(video_files[0])
    if not reference_info:
        output_text.insert(tk.END, f"❌ Error reading {video_files[0]}\n")
        return False

    for video in video_files[1:]:
        info = get_video_info(video)
        if info != reference_info:
            output_text.insert(tk.END, f"❌ Incompatible file detected: {os.path.basename(video)}\n")
            return False

    output_text.insert(tk.END, "✅ All videos are compatible!\n")
    return True


def create_concat_file(video_files, folder_path):
    concat_file = os.path.join(folder_path, "concat_list.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for video in video_files:
            f.write(f"file '{video}'\n")
    return concat_file


def average_list(myList):
    return sum(myList) / len(myList) if myList else 0


def join_videos(concat_file, output_file, total_files, output_text, root):
    ffmpeg_cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy", "-progress", "pipe:1", "-nostats", output_file
    ]

    try:
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

        output_text.insert(tk.END, "\n🚀 Starting FFmpeg to join videos...\n")
        output_text.see(tk.END)

        progress_line_index = output_text.index(tk.END)
        output_text.insert(tk.END, f"🟢 [0/{total_files}] Progress: Starting...\n")
        output_text.see(tk.END)

        start_time = time.perf_counter()
        avg_time_diff = [0] * 10
        i = 0

        for line in process.stdout:
            match = re.search(r"frame=\s*(\d+)", line)
            if match:
                now = time.perf_counter()
                elapsed = now - start_time
                avg_time_diff[i] = elapsed
                estimated_total_time = average_list(avg_time_diff) * total_files
                elapsed_total_time = now - start_time
                percentage = (elapsed_total_time / estimated_total_time) * 100 if estimated_total_time else 0
                i = (i + 1) % 10

                progress_message = f"🟢 [~/{total_files}] Progress: {percentage:.2f}% elapsed."
                output_text.delete(progress_line_index, f"{progress_line_index} lineend")
                output_text.insert(progress_line_index, progress_message)
                output_text.see(tk.END)

        process.wait()

        if process.returncode == 0:
            output_text.insert(tk.END, f"\n✅ Successfully joined videos into: {output_file}\n")
        else:
            output_text.insert(tk.END, "\n❌ FFmpeg failed! Check the output above for details.\n")

        output_text.see(tk.END)
        root.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been joined!"), root.destroy()))

    except FileNotFoundError:
        messagebox.showerror("Error", "FFmpeg not found! Make sure it's installed and added to PATH.")


def process_folder(folder_path, output_text, root):
    supported_formats = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")
    video_files = sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(supported_formats)
    ])
    total_files = len(video_files)

    if total_files < 2:
        output_text.insert(tk.END, "❌ Need at least two compatible videos to join.\n")
        return

    output_text.insert(tk.END, f"\n📂 Found {total_files} video files to join.\n")
    output_text.see(tk.END)

    if not check_compatibility(video_files, output_text):
        messagebox.showerror("Incompatible Videos", "Videos have different properties and can't be joined.")
        return

    concat_file = create_concat_file(video_files, folder_path)
    output_file = os.path.join(folder_path, "joined_output.mp4")

    join_videos(concat_file, output_file, total_files, output_text, root)


def select_folder(output_text, root):
    global WINBOLL
    folder_path = filedialog.askdirectory(title="Select a Folder Containing Videos")
    if folder_path:
        output_text.insert(tk.END, f"📁 Selected folder: {folder_path}\n")
        output_text.see(tk.END)
        Thread(target=process_folder, args=(folder_path, output_text, root)).start()
    else:
        WINBOLL = False


def main(windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    root = tk.Tk()
    root.configure(bg=windowBg)
    root.title("Video Joiner")
    root.iconify()

    output_text = tk.Text(root, height=20, width=80, bg=buttonBg, fg="white")
    output_text.pack()

    select_folder(output_text, root)
    if WINBOLL:
        root.deiconify()
        root.mainloop()
    else:
        root.destroy()


if __name__ == '__main__':
    main()
