import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread
import time
import re
from .constants import (
    SUPPORTED_VIDEO_FORMATS, JOINED_OUTPUT_FILENAME, CONCAT_LIST_FILENAME,
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    CANCEL_BUTTON_BG, CANCEL_BUTTON_ACTIVE_BG, CANCELLATION_MESSAGE_DELAY,
    PROCESS_TERMINATION_TIMEOUT, JOINER_WINDOW_TITLE
)
from .ConfigManager import get_config_manager


WINBOOL = True

# Global variables for cancel functionality
_current_process = None
_cancel_requested = False


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
    """Create FFmpeg concat file with properly escaped paths.
    
    FFmpeg concat demuxer requires:
    - Absolute paths (or relative with -safe 0)
    - Single quotes escaped if present in path
    - Forward slashes on Windows for better compatibility
    """
    concat_file = os.path.join(folder_path, CONCAT_LIST_FILENAME).replace("\\", "/")
    
    with open(concat_file, "w", encoding="utf-8") as f:
        for video in video_files:
            # Convert to absolute path and normalize
            abs_path = os.path.abspath(video)
            # Use forward slashes for Windows compatibility with FFmpeg
            normalized_path = abs_path.replace("\\", "/")
            # Escape single quotes in path (FFmpeg concat format: ' becomes '\'')
            escaped_path = normalized_path.replace("'", "'\\''")
            # Write in FFmpeg concat format
            f.write(f"file '{escaped_path}'\n")
    
    return concat_file


def average_list(myList):
    return sum(myList) / len(myList) if myList else 0


def join_videos(concat_file, output_file, total_files, output_text, root):
    global _current_process, _cancel_requested
    
    # Reset cancel flag
    _cancel_requested = False
    
    ffmpeg_cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy", "-progress", "pipe:1", "-nostats", output_file
    ]

    try:
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        _current_process = process

        output_text.insert(tk.END, "\n🚀 Starting FFmpeg to join videos...\n")
        output_text.see(tk.END)

        progress_line_index = output_text.index(tk.END)
        output_text.insert(tk.END, f"🟢 [0/{total_files}] Progress: Starting...\n")
        output_text.see(tk.END)

        start_time = time.perf_counter()
        avg_time_diff = [0] * 10
        i = 0

        for line in process.stdout:
            # Check for cancellation
            if _cancel_requested:
                process.terminate()
                try:
                    process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                output_text.insert(tk.END, "\n⚠️ Operation cancelled by user\n")
                output_text.see(tk.END)
                _current_process = None
                # Clean up partial output file
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        output_text.insert(tk.END, f"\n🗑️ Partial output file removed.\n")
                    except Exception as e:
                        pass
                # Close window after showing cancellation message
                root.after(CANCELLATION_MESSAGE_DELAY, lambda: (messagebox.showinfo("Cancelled", "Operation was cancelled."), root.destroy()))
                return
            
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
        _current_process = None

        if _cancel_requested:
            return

        if process.returncode == 0:
            output_text.insert(tk.END, f"\n✅ Successfully joined videos into: {output_file}\n")
        else:
            output_text.insert(tk.END, "\n❌ FFmpeg failed! Check the output above for details.\n")

        output_text.see(tk.END)
        root.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been joined!"), root.destroy()))

    except FileNotFoundError:
        _current_process = None
        messagebox.showerror("Error", "FFmpeg not found! Make sure it's installed and added to PATH.")
    except Exception as e:
        _current_process = None
        output_text.insert(tk.END, f"\n❌ Error: {str(e)}\n")
        output_text.see(tk.END)


def process_folder(folder_path, output_text, root, output_folder=None):
    video_files = sorted([
        os.path.join(folder_path, f).replace("\\", "/")
        for f in os.listdir(folder_path)
        if f.lower().endswith(SUPPORTED_VIDEO_FORMATS)
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
    
    # Use output_folder if provided, otherwise use input folder
    if output_folder:
        output_file = os.path.join(output_folder, JOINED_OUTPUT_FILENAME).replace("\\", "/")
    else:
        output_file = os.path.join(folder_path, JOINED_OUTPUT_FILENAME).replace("\\", "/")

    join_videos(concat_file, output_file, total_files, output_text, root)


def select_folder(output_text, root):
    global WINBOOL
    config = get_config_manager()
    last_join_input_folder = config.get_last_join_input_folder()
    
    root.iconify()
    folder_path = filedialog.askdirectory(
        title="Select a Folder Containing Videos",
        initialdir=last_join_input_folder if last_join_input_folder and os.path.exists(last_join_input_folder) else None
    )
    root.deiconify()
    
    if folder_path:
        # Save input folder
        config.set_last_join_input_folder(folder_path)
        
        # Ask for output folder
        last_join_output_folder = config.get_last_join_output_folder()
        root.iconify()
        output_folder = filedialog.askdirectory(
            title="Select Output Folder (or Cancel to use same folder as input)",
            initialdir=last_join_output_folder if last_join_output_folder and os.path.exists(last_join_output_folder) else folder_path
        )
        root.deiconify()
        
        # Save output folder if selected
        if output_folder:
            config.set_last_join_output_folder(output_folder)
        
        output_text.insert(tk.END, f"📁 Selected folder: {folder_path}\n")
        if output_folder:
            output_text.insert(tk.END, f"📂 Output folder: {output_folder}\n")
        else:
            output_text.insert(tk.END, f"📂 Output folder: Same as input\n")
        output_text.see(tk.END)
        Thread(target=process_folder, args=(folder_path, output_text, root, output_folder)).start()
    else:
        WINBOOL = False


def cancel_operation():
    """Cancel the current video joining operation."""
    global _current_process, _cancel_requested
    _cancel_requested = True
    if _current_process:
        try:
            _current_process.terminate()
        except Exception as e:
            pass


def main(windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    root = tk.Tk()
    root.configure(bg=windowBg)
    root.title(JOINER_WINDOW_TITLE)
    root.iconify()

    output_text = tk.Text(root, height=20, width=80, bg=buttonBg, fg="white")
    output_text.pack(pady=10)
    
    # Add cancel button
    cancel_button = tk.Button(root, text="❌ Cancel Operation", command=cancel_operation, 
                              bg=CANCEL_BUTTON_BG, fg="white", font=("Arial", "10", "bold"),
                              activebackground=CANCEL_BUTTON_ACTIVE_BG, activeforeground="white", borderwidth=2)
    cancel_button.pack(pady=5)

    select_folder(output_text, root)
    if WINBOOL:
        root.deiconify()
        root.mainloop()
    else:
        root.destroy()


if __name__ == '__main__':
    main()
