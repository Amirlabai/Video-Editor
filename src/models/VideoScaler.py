import sys
import threading
import tkinter as tk
from tkinter import *
from tkinter import filedialog, messagebox
import subprocess
import os
import re
import time
from threading import Thread
from datetime import datetime
import multiprocessing
import logging
from pathlib import Path
from .constants import (
    HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT, UHD_4K_WIDTH, UHD_4K_HEIGHT,
    DEFAULT_CRF, HIGH_QUALITY_CRF, MEDIUM_QUALITY_CRF, LOW_QUALITY_CRF,
    CRF_MIN, CRF_MAX, DEFAULT_PRESET,
    DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE,
    CPU_CODEC, GPU_CODEC,
    DEFAULT_WINDOW_BG, DEFAULT_BUTTON_BG, DEFAULT_ACTIVE_BUTTON_BG,
    CANCEL_BUTTON_BG, CANCEL_BUTTON_ACTIVE_BG,
    DEFAULT_WINDOW_TITLE, CANCELLATION_MESSAGE_DELAY, SUCCESS_MESSAGE_DELAY,
    LOG_DIR_NAME, LOG_FILENAME
)

WINBOOL = True

# Global variables for cancel functionality
_current_process = None
_cancel_requested = False

# Setup logging
def setup_logger():
    """Setup logging configuration."""
    log_dir = Path.home() / LOG_DIR_NAME
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / LOG_FILENAME
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

def sanitize_path(file_path):
    """Sanitize file path to prevent path injection attacks.
    
    Args:
        file_path: Input file path
        
    Returns:
        str: Sanitized absolute path, or None if invalid
    """
    try:
        # Convert to Path object and resolve to absolute path
        path = Path(file_path).resolve()
        
        # Check if path exists and is a file
        if not path.exists():
            logger.warning(f"Path does not exist: {file_path}")
            return None
            
        # Return as string
        return str(path)
    except (ValueError, OSError) as e:
        logger.error(f"Invalid path: {file_path} - {e}")
        return None

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
        if len(output_lines)>2:
            duration_str = output_lines[-1]
        else:
            duration_str = output_lines[1]
        fps_str = output_lines[0].split("/")[0]
        if int(fps_str) == 0:
            fps_str = output_lines[1].split("/")[0]
        return int(int(float(duration_str)) * int(fps_str))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError) as e:
        logger.error(f"Error getting total frames for {video_path}: {e}")
        return None


def average_list(myList):
    tot = sum(myList)
    return float(tot / len(myList)) if myList else 0

def process_ffmpeg_output(process, output_text, progress_line_index, total_frames, error_list, input_file):
    """Process FFmpeg stdout output, track progress, and capture errors.
    
    Returns:
        tuple: (return_code, error_list) - Process return code and updated error list
    """
    start_time = time.perf_counter()
    tot_time = start_time
    prev_frames = 0
    avg_frame_diff = [0] * 50
    avg_time_diff = [0] * 50
    avg_frame = 0
    avg_time = 0
    i = 0
    j = 0
    
    error_patterns = [
        r'\[error\]',
        r'Error',
        r'error',
        r'ERROR',
        r'Failed',
        r'failed',
        r'FAILED',
        r'Impossible',
        r'impossible',
        r'Could not',
        r'could not',
        r'Cannot',
        r'cannot',
        r'Invalid',
        r'invalid',
        r'not found',
        r'Not found',
        r'NOT FOUND',
        r'Permission denied',
        r'permission denied',
        r'No such file',
        r'no such file',
        r'Hardware is lacking',
        r'hardware is lacking',
        r'Function not implemented',
        r'function not implemented'
    ]

    for line in process.stdout:
        # Check for cancellation
        global _cancel_requested
        if _cancel_requested:
            logger.info("Cancel requested, terminating FFmpeg process")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            output_text.insert(tk.END, "\n⚠️ Operation cancelled by user\n")
            output_text.see(tk.END)
            return -1, error_list
        
        # Check for error patterns in each line
        for pattern in error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                error_list.append(line.strip())
                break
        
        match = re.search(r"frame=\s*(\d+)", line)
        if match:
            frames = int(match.group(1))
            if total_frames:
                frame_diff = frames - prev_frames
                now = time.perf_counter()
                elapsed = now - start_time
                
                avg_frame_diff[i] = frame_diff
                avg_time_diff[i] = elapsed
                if j == 0:
                    avg_frame = average_list(avg_frame_diff)
                    avg_time = average_list(avg_time_diff)
                    i = (i + 1) % 50

                if avg_time > 0 and avg_frame > 0:
                    remaining_time = ((total_frames - frames) / (avg_frame / avg_time))
                else:
                    remaining_time = 0
                
                remaining_time = int(remaining_time)
                hours, minutes = divmod(remaining_time, 3600)
                minutes, seconds = divmod(minutes, 60)
                percent = (frames / total_frames) * 100
                progress_message = f"🟢 Progress: {frames}/{total_frames} frames ({percent:.2f}%) avg frame: {avg_frame} | Running: {(now - tot_time)/60:.2f} - Remaining: {hours:02}:{minutes:02}:{seconds:02}"

                output_text.delete(progress_line_index, f"{progress_line_index} lineend")
                output_text.insert(progress_line_index, progress_message)
                output_text.see(tk.END)

                prev_frames = frames
                start_time = now
                j = (j + 1) % 5

    return_code = process.wait()
    return return_code, error_list

def get_ffmpeg_error_code(return_code):
    """Look up FFmpeg return code meanings."""
    error_codes = {
        0: "Success",
        1: "Unknown error",
        -1: "Process terminated",
        -2: "Invalid argument",
        -3: "No such file or directory",
        -4: "Permission denied",
        -5: "I/O error",
        -6: "No space left on device",
        -7: "Out of memory",
        -8: "Invalid data found",
        -9: "Operation not permitted",
        -10: "Protocol error",
        -11: "Not found",
        -12: "Not available",
        -13: "Invalid",
        -14: "EOF",
        -15: "Not implemented",
        -16: "Bug",
        -17: "Unknown error",
        -18: "Experimental",
        -19: "Input changed",
        -20: "Output changed",
        -22: "Invalid argument",
        -40: "Function not implemented",
        -50: "Invalid argument",
        -100: "Unknown error"
    }
    return error_codes.get(return_code, f"Unknown error code: {return_code}")

def check_gpu_compatibility():
    """Check if GPU (NVENC) is available via ffmpeg."""
    try:
        # Check if h264_nvenc encoder is available
        cmd = ["ffmpeg", "-hide_banner", "-encoders"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        if "h264_nvenc" in result.stdout:
            return True
        return False
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

def get_cpu_cores():
    """Get the number of CPU cores available."""
    return multiprocessing.cpu_count()

def get_performance_settings(root, windowBg='#1e1e1e', buttonBg='#323232', activeButtonBg='#192332'):
    """Dialog to get performance settings: threading and GPU usage."""
    perf_window = tk.Toplevel(root)
    perf_window.configure(bg=windowBg)
    perf_window.title("Performance Settings")
    perf_window.grab_set()
    
    use_gpu = tk.BooleanVar(perf_window, value=False)
    use_all_cores = tk.BooleanVar(perf_window, value=False)
    gpu_available = check_gpu_compatibility()
    cpu_cores = get_cpu_cores()
    
    def confirm_settings():
        perf_window.destroy()
    
    # GPU option
    if gpu_available:
        gpu_label = tk.Label(perf_window, text="🚀 GPU (NVENC) Available!", bg=windowBg, fg="#4CAF50", 
                            font=("Arial", "12", "bold"))
        gpu_label.grid(row=0, column=0, columnspan=2, pady=10, padx=10)
        
        gpu_checkbox = tk.Checkbutton(perf_window, text="Use GPU encoding (Much Faster!)", 
                                      variable=use_gpu, bg=windowBg, fg="white",
                                      selectcolor=activeButtonBg, font=("Arial", "10", "bold"))
        gpu_checkbox.grid(row=1, column=0, columnspan=2, pady=5, padx=10, sticky="w")
    else:
        gpu_label = tk.Label(perf_window, text="⚠️ GPU (NVENC) Not Available", bg=windowBg, fg="#FF9800", 
                            font=("Arial", "12", "bold"))
        gpu_label.grid(row=0, column=0, columnspan=2, pady=10, padx=10)
        
        gpu_info = tk.Label(perf_window, text="Using CPU encoding", bg=windowBg, fg="white", 
                           font=("Arial", "9"))
        gpu_info.grid(row=1, column=0, columnspan=2, pady=5, padx=10)
    
    # Threading option
    threading_label = tk.Label(perf_window, text="CPU Threading", bg=windowBg, fg="white", 
                              font=("Arial", "12", "bold"))
    threading_label.grid(row=2, column=0, columnspan=2, pady=(20, 5), padx=10)
    
    cores_info = tk.Label(perf_window, text=f"Available CPU cores: {cpu_cores}", bg=windowBg, fg="white", 
                         font=("Arial", "9"))
    cores_info.grid(row=3, column=0, columnspan=2, pady=5, padx=10)
    
    threading_checkbox = tk.Checkbutton(perf_window, 
                                        text=f"Use all CPU cores (Default: FFmpeg auto, All cores: {cpu_cores} threads)", 
                                        variable=use_all_cores, bg=windowBg, fg="white",
                                        selectcolor=activeButtonBg, font=("Arial", "10", "bold"))
    threading_checkbox.grid(row=4, column=0, columnspan=2, pady=5, padx=10, sticky="w")
    
    # Confirm button
    confirm_button = tk.Button(perf_window, text="Confirm", command=confirm_settings, 
                              bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                              activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    confirm_button.grid(row=5, column=0, columnspan=2, pady=20, padx=10)
    
    perf_window.wait_window()
    
    return use_gpu.get(), use_all_cores.get(), cpu_cores

def extract_ratio(folder_path,filename):
    orientation = ""
    xaxis = "0"
    yaxis = "0"
    crfValue = "28"
    preset = "medium"

    file_path = f"{folder_path}/{filename}"

    try:
        # Construct the ffmpeg command to get video stream information
        command = [
            'ffprobe',
            '-v',
            'error',
            '-select_streams',
            'v:0',
            '-show_entries',
            'stream=width,height',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
            file_path
        ]

        # Execute the ffmpeg command
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        output = process.stdout.strip()
        width_str, height_str = output.split('\n')
        width = int(width_str)
        height = int(height_str)
        bool_ratio = True

        # Determine orientation and set xaxis and yaxis
        if width > height:
            orientation = "horizontal"
            xaxis = "1280"
            yaxis = "720"
        elif height > width:
            orientation = "vertical"
            xaxis = "720"
            yaxis = "1280"
            bool_ratio = False
        else:
            orientation = "square" # Handle cases where width and height are equal
            xaxis = "720" # You can adjust these values as needed for square videos
            yaxis = "720"

        return bool_ratio, orientation, xaxis, yaxis, crfValue, preset

    except FileNotFoundError:
        logger.error(f"File not found at {file_path}")
        return False, orientation, xaxis, yaxis, crfValue, preset
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running ffprobe for {file_path}: {e}")
        logger.debug(f"FFprobe stderr: {e.stderr}")
        return False, orientation, xaxis, yaxis, crfValue, preset
    except ValueError as e:
        logger.error(f"Error parsing ffprobe output for {file_path}: {output}")
        return False, orientation, xaxis, yaxis, crfValue, preset

def get_ratio(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    VH_window = tk.Toplevel(root)
    VH_window.configure(bg=windowBg)
    VH_window.title("Choose Orientation")
    VH_window.grab_set()

    orientation = tk.StringVar(VH_window, value="")
    xaxis = tk.StringVar(VH_window, value="1280")
    yaxis = tk.StringVar(VH_window, value="720")
    crfValue = tk.StringVar(VH_window, value="23")
    preset = tk.StringVar(VH_window, value="medium")
    selected = tk.BooleanVar(VH_window)

    def set_horizontal():
        orientation.set("_horizontal")
        selected.set(False)
        rez = get_pixel(root, windowBg, buttonBg, activeButtonBg)
        xaxis.set(rez[0])
        yaxis.set(rez[1])
        crfValue.set(get_crf(root,windowBg, buttonBg, activeButtonBg))
        preset.set(get_preset(root,windowBg, buttonBg, activeButtonBg))
        VH_window.destroy()

    def set_vertical():
        orientation.set("_vertical")
        selected.set(True)
        rez = get_pixel(root,windowBg, buttonBg, activeButtonBg)
        xaxis.set(rez[0])
        yaxis.set(rez[1])
        crfValue.set(get_crf(root,windowBg, buttonBg, activeButtonBg))
        preset.set(get_preset(root, windowBg, buttonBg, activeButtonBg))
        VH_window.destroy()

    def close_window():
        # Return default settings when "default settings" is clicked
        orientation.set("_horizontal")
        selected.set(False)
        VH_window.destroy()


    label = tk.Label(VH_window, text="video Orientation", bg=windowBg, fg="white", font=("Arial", "16", "bold"))
    label.grid(row=0,column=0,columnspan=2)

    horizontal_button = tk.Button(VH_window, text="Horizontal", command=set_horizontal, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    horizontal_button.grid(row=1, column=0, pady=10, padx=5)

    vertical_button = tk.Button(VH_window, text="Vertical", command=set_vertical, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.grid(row=1, column=1, pady=10, padx=5)

    horizontal_button = tk.Button(VH_window, text="default settings", command=close_window, bg=buttonBg, fg="white",
                                  font=("Arial", "10", "bold"),
                                  activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    horizontal_button.grid(row=2, column=0,columnspan=2, pady=10, padx=5)

    VH_window.wait_window()

    # If closed without selection
    if orientation.get() == "":
        return False, "_horizontal", str(HD_WIDTH), str(HD_HEIGHT), HIGH_QUALITY_CRF, DEFAULT_PRESET
    else:
        return selected.get(), orientation.get(), xaxis.get(), yaxis.get(),crfValue.get(), preset.get()


def get_pixel(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    VH_window = tk.Toplevel(root)
    VH_window.configure(bg=windowBg)
    VH_window.title("Choose pixels")
    VH_window.grab_set()

    x = tk.IntVar(VH_window, value=HD_WIDTH)
    y = tk.IntVar(VH_window, value=HD_HEIGHT) 
    selected = tk.BooleanVar(VH_window)

    def set_hd():
        selected.set(False)
        VH_window.destroy()

    def set_fhd():
        selected.set(True)
        x.set(FHD_WIDTH)
        y.set(FHD_HEIGHT)
        VH_window.destroy()

    def set_4k():
        selected.set(True)
        x.set(UHD_4K_WIDTH)
        y.set(UHD_4K_HEIGHT)
        VH_window.destroy()

    label = tk.Label(VH_window, text="Video Resolution", bg=windowBg, fg="white", font=("Arial", "16", "bold"))
    label.grid(row=0, column=0, columnspan=2)

    horizontal_button = tk.Button(VH_window, text=f"HD:{HD_WIDTH}x{HD_HEIGHT}", command=set_hd, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    horizontal_button.grid(row=1, column=0, pady=10, padx=5)

    vertical_button = tk.Button(VH_window, text=f"FHD:{FHD_WIDTH}x{FHD_HEIGHT}", command=set_fhd, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.grid(row=1, column=1, pady=10, padx=5)

    vertical_button = tk.Button(VH_window, text=f"4K:{UHD_4K_WIDTH}x{UHD_4K_HEIGHT}", command=set_4k, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.grid(row=1, column=2, pady=10, padx=5)

    VH_window.wait_window()

    # Return the selected resolution values
    # Note: selected flag indicates if user chose FHD/4K (True) or HD (False)
    # but we return the actual x, y values which are already set correctly
    return x.get(), y.get()


def get_crf(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    VH_window = tk.Toplevel(root)
    VH_window.configure(bg=windowBg)
    VH_window.title("Choose lossless range")
    VH_window.grab_set()

    crf = tk.StringVar(VH_window,value="")

    def set_crf():
        crf.set(str(int(horizontal_slider.get())))
        VH_window.destroy()

    label = tk.Label(VH_window, text="Video Encoding", bg=windowBg, fg="white", font=("Arial", "16", "bold"))
    label.pack(padx=10,pady=5)
    label_2 = tk.Label(VH_window, text="the lower the better", bg=windowBg, fg="white", font=("Arial", "10", "bold"))
    label_2.pack(padx=10,pady=5)

    horizontal_slider = tk.Scale(VH_window, from_=CRF_MIN, to=CRF_MAX, orient=HORIZONTAL, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                                 activebackground=activeButtonBg, borderwidth=2)
    horizontal_slider.pack(padx=10,pady=5)
    horizontal_slider.set(int(DEFAULT_CRF))

    vertical_button = tk.Button(VH_window, text="Set", command=set_crf, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.pack(padx=10,pady=5)

    VH_window.wait_window()

    # If closed without selection, return default
    if crf.get() == "":
        return DEFAULT_CRF
    else:
        return crf.get()


def get_preset(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    gp_window = tk.Toplevel(root)
    gp_window.configure(bg=windowBg)
    gp_window.title("Choose preset")
    gp_window.grab_set()

    preset = tk.StringVar(gp_window, value="")

    def set_preset(text):
        preset.set(text)
        gp_window.destroy()

    label = tk.Label(gp_window, text="Video Preset", bg=windowBg, fg="white", font=("Arial", "16", "bold"))
    label.grid(row=0, column=0, columnspan=5)

    horizontal_button = tk.Button(gp_window, text="superfast", command=lambda: set_preset('superfast'), bg=buttonBg, fg="white",
                                  font=("Arial", "10", "bold"),
                                  activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    horizontal_button.grid(row=1, column=0, pady=10, padx=5)

    horizontal_button = tk.Button(gp_window, text="fast", command=lambda: set_preset('fast'), bg=buttonBg, fg="white",
                                  font=("Arial", "10", "bold"),
                                  activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    horizontal_button.grid(row=1, column=1, pady=10, padx=5)

    horizontal_button = tk.Button(gp_window, text="medium", command=lambda: set_preset('medium'), bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    horizontal_button.grid(row=1, column=2, pady=10, padx=5)

    vertical_button = tk.Button(gp_window, text="Slow", command=lambda: set_preset('slow'), bg=buttonBg, fg="white",
                                font=("Arial", "10", "bold"),
                                activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.grid(row=1, column=3, pady=10, padx=5)

    vertical_button = tk.Button(gp_window, text="veryslow", command=lambda: set_preset('veryslow'), bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.grid(row=1, column=4, pady=10, padx=5)

    gp_window.wait_window()

    # If closed without selection
    return preset.get()


def scale_video_CPU(input_file, output_file, total_frames, output_text, root, ratio=False, xaxis=str(HD_WIDTH), yaxis=str(HD_HEIGHT), crf=DEFAULT_CRF, preset=DEFAULT_PRESET, threads=0):
    global _current_process, _cancel_requested
    
    # Reset cancel flag
    _cancel_requested = False

    if ratio:   #   if True vertical
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", f"scale={yaxis}:{xaxis}",
            "-c:v", CPU_CODEC, "-crf", crf, "-preset", preset,
            "-threads", str(threads),
            "-c:a", DEFAULT_AUDIO_CODEC, "-b:a", DEFAULT_AUDIO_BITRATE,
            "-progress", "pipe:1", "-nostats",
            output_file
        ]
    else:   # false hroizontal
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", f"scale={xaxis}:{yaxis}",
            "-c:v", CPU_CODEC, "-crf", crf, "-preset", preset,
            "-threads", str(threads),
            "-c:a", DEFAULT_AUDIO_CODEC, "-b:a", DEFAULT_AUDIO_BITRATE,
            "-progress", "pipe:1", "-nostats",
            output_file
        ]
    
    # Initialize error list before try block so it's available in exception handlers
    error_list = []

    try:
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        _current_process = process

        threading_info = f" with {threads} threads" if threads > 0 else " (auto threading)"
        output_text.insert(tk.END, f"🚀 Starting FFmpeg{threading_info}...\n")
        output_text.see(tk.END)

        # Placeholder for progress line
        progress_line_index = output_text.index(tk.END)
        output_text.insert(tk.END, f"🟢 {input_file} Starting...\n")
        output_text.see(tk.END)

        # Process FFmpeg output and track progress
        return_code, error_list = process_ffmpeg_output(process, output_text, progress_line_index, total_frames, error_list, input_file)
        
        # Clear process reference
        _current_process = None
        
        # Handle cancellation
        if _cancel_requested or return_code == -1:
            # Clean up partial output file
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                    logger.info(f"Removed partial output file: {output_file}")
                    output_text.insert(tk.END, f"\n🗑️ Partial output file removed.\n")
                except Exception as e:
                    logger.warning(f"Could not remove partial file: {e}")
            output_text.insert(tk.END, f"\n⚠️ Operation cancelled by user.\n")
            output_text.see(tk.END)
            # Close window after showing cancellation message
            root.after(CANCELLATION_MESSAGE_DELAY, lambda: (messagebox.showinfo("Cancelled", "Operation was cancelled."), root.destroy()))
            return
        
        # Check return code and log errors
        if return_code != 0 or len(error_list) > 0:
            error_msg = get_ffmpeg_error_code(return_code)
            output_text.insert(tk.END, f"\n❌ CPU Encoding Error (Return Code: {return_code})\n")
            output_text.insert(tk.END, f"Error Code Meaning: {error_msg}\n")
            output_text.insert(tk.END, f"Input file: {input_file}\n")
            output_text.insert(tk.END, f"Output file: {output_file}\n")
            
            # Display all captured errors
            if len(error_list) > 0:
                output_text.insert(tk.END, f"\n📋 Captured Errors ({len(error_list)} total):\n")
                for idx, error in enumerate(error_list, 1):
                    output_text.insert(tk.END, f"  {idx}. {error}\n")
            else:
                output_text.insert(tk.END, f"\n⚠️ No specific error messages captured, but process failed.\n")
            
            output_text.see(tk.END)
            
            # Create error summary for dialog
            error_summary = f"CPU encoding failed!\n\nReturn Code: {return_code}\nError: {error_msg}\n\n"
            if len(error_list) > 0:
                error_summary += f"Captured {len(error_list)} error(s):\n"
                for idx, error in enumerate(error_list[:5], 1):  # Show first 5 errors
                    error_summary += f"{idx}. {error[:100]}\n"  # Truncate long errors
                if len(error_list) > 5:
                    error_summary += f"... and {len(error_list) - 5} more errors\n"
            error_summary += "\nCheck the output log for full details."
            
            root.after(100, lambda: messagebox.showerror("Encoding Error", error_summary))
            return
        
        output_text.insert(tk.END, f"\n✅ CPU encoding completed successfully!\n")
        output_text.see(tk.END)
        root.after(SUCCESS_MESSAGE_DELAY, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), root.destroy()))

    except FileNotFoundError:
        error_list.append("FFmpeg not found! Make sure it's installed and added to PATH.")
        output_text.insert(tk.END, "\n❌ Error: FFmpeg not found! Make sure it's installed and added to PATH.\n")
        output_text.insert(tk.END, f"📋 Captured Errors:\n  1. {error_list[0]}\n")
        output_text.see(tk.END)
        messagebox.showerror("Error", "FFmpeg not found! Make sure it's installed and added to PATH.")
    except Exception as e:
        error_list.append(f"Exception: {str(e)}")
        output_text.insert(tk.END, f"\n❌ CPU Encoding Exception: {str(e)}\n")
        output_text.insert(tk.END, f"📋 Captured Errors:\n  1. {error_list[0]}\n")
        output_text.see(tk.END)
        root.after(100, lambda: messagebox.showerror("Encoding Error", f"CPU encoding exception:\n{str(e)}"))

def scale_video_GPU(input_file, output_file, total_frames, output_text, root, ratio=False, xaxis=str(HD_WIDTH), yaxis=str(HD_HEIGHT), crf=DEFAULT_CRF, preset=DEFAULT_PRESET):
    global _current_process, _cancel_requested
    
    # Reset cancel flag
    _cancel_requested = False
    # Sanitize file paths
    input_file = sanitize_path(input_file)
    if input_file is None:
        output_text.insert(tk.END, f"\n❌ Error: Invalid input file path\n")
        output_text.see(tk.END)
        return
    
    output_file = sanitize_path(os.path.dirname(output_file)) or os.path.dirname(output_file)
    output_file = os.path.join(output_file, os.path.basename(output_file))
    
    # Map CPU presets to NVENC-compatible presets
    nvenc_preset_map = {
        "superfast": "fast",
        "fast": "fast",
        "medium": "medium",
        "slow": "slow",
        "veryslow": "slow"
    }
    nvenc_preset = nvenc_preset_map.get(preset, "medium")
    
    # Convert CRF to CQ (NVENC uses -cq instead of -crf)
    # NVENC CQ range is typically 0-51, similar to CRF
    try:
        cq_value = str(int(crf))
        if not (0 <= int(cq_value) <= 51):
            logger.warning(f"CQ value {cq_value} out of range, using 26")
            cq_value = DEFAULT_CRF
    except ValueError:
        logger.warning(f"Invalid CQ value {crf}, using 26")
        cq_value = "26"

    if ratio:   #   if True vertical
        # Simplified approach: CPU decoding/scaling, GPU encoding
        # This avoids CUDA hardware acceleration issues while still using GPU for encoding
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_file,
            "-vf", f"scale={yaxis}:{xaxis}",
            "-c:v", GPU_CODEC,
            "-preset", nvenc_preset,
            "-rc", "vbr",
            "-cq", cq_value,
            "-c:a", DEFAULT_AUDIO_CODEC,
            "-b:a", DEFAULT_AUDIO_BITRATE,
            "-pix_fmt", "yuv420p",
            "-progress", "pipe:1",
            "-nostats",
            output_file
        ]
    else:   # false horizontal
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_file,
            "-vf", f"scale={xaxis}:{yaxis}",
            "-c:v", GPU_CODEC,
            "-preset", nvenc_preset,
            "-rc", "vbr",
            "-cq", cq_value,
            "-c:a", DEFAULT_AUDIO_CODEC,
            "-b:a", DEFAULT_AUDIO_BITRATE,
            "-pix_fmt", "yuv420p",
            "-progress", "pipe:1",
            "-nostats",
            output_file
        ]
    
    # Initialize error list before try block so it's available in exception handlers
    error_list = []

    try:
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        _current_process = process

        output_text.insert(tk.END, "🚀 Starting FFmpeg with GPU acceleration (NVENC)...\n")
        output_text.see(tk.END)

        # Placeholder for progress line
        progress_line_index = output_text.index(tk.END)
        output_text.insert(tk.END, f"🟢 {input_file} Starting...\n")
        output_text.see(tk.END)

        # Process FFmpeg output and track progress
        return_code, error_list = process_ffmpeg_output(process, output_text, progress_line_index, total_frames, error_list, input_file)
        
        # Clear process reference
        _current_process = None
        
        # Handle cancellation
        if _cancel_requested or return_code == -1:
            # Clean up partial output file
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                    logger.info(f"Removed partial output file: {output_file}")
                    output_text.insert(tk.END, f"\n🗑️ Partial output file removed.\n")
                except Exception as e:
                    logger.warning(f"Could not remove partial file: {e}")
            output_text.insert(tk.END, f"\n⚠️ Operation cancelled by user.\n")
            output_text.see(tk.END)
            # Close window after showing cancellation message
            root.after(CANCELLATION_MESSAGE_DELAY, lambda: (messagebox.showinfo("Cancelled", "Operation was cancelled."), root.destroy()))
            return
        
        # Check for NVENC DLL loading errors specifically
        nvenc_dll_error = any("Cannot load nvEncodeAPI64.dll" in err or "nvEncodeAPI" in err for err in error_list)
        
        # Check return code and log errors
        if return_code != 0 or len(error_list) > 0:
            error_msg = get_ffmpeg_error_code(return_code)
            output_text.insert(tk.END, f"\n❌ GPU Encoding Error (Return Code: {return_code})\n")
            output_text.insert(tk.END, f"Error Code Meaning: {error_msg}\n")
            output_text.insert(tk.END, f"Input file: {input_file}\n")
            output_text.insert(tk.END, f"Output file: {output_file}\n")
            
            # Display all captured errors
            if len(error_list) > 0:
                output_text.insert(tk.END, f"\n📋 Captured Errors ({len(error_list)} total):\n")
                for idx, error in enumerate(error_list, 1):
                    output_text.insert(tk.END, f"  {idx}. {error}\n")
            else:
                output_text.insert(tk.END, f"\n⚠️ No specific error messages captured, but process failed.\n")
            
            # Check if NVENC DLL error and offer fallback
            if nvenc_dll_error:
                output_text.insert(tk.END, f"\n⚠️ NVENC DLL not available. GPU encoding cannot be used.\n")
                output_text.insert(tk.END, f"💡 Falling back to CPU encoding...\n")
                output_text.see(tk.END)
                
                # Fallback to CPU encoding
                root.after(100, lambda: messagebox.showwarning("GPU Unavailable", 
                    "GPU encoding failed because NVENC DLL is not available.\n\n"
                    "This usually means:\n"
                    "- NVIDIA drivers are not installed\n"
                    "- FFmpeg was not built with NVENC support\n"
                    "- GPU hardware doesn't support NVENC\n\n"
                    "Falling back to CPU encoding..."))
                
                # Call CPU encoding function instead
                # Delete output file first if it exists
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        output_text.insert(tk.END, f"\n🗑️ Existing output file '{output_file}' deleted before CPU encoding fallback.\n")
                        output_text.see(tk.END)
                    except Exception as e:
                        output_text.insert(tk.END, f"\n⚠️ Could not delete existing output file '{output_file}': {str(e)}\n")
                        output_text.see(tk.END)
                scale_video_CPU(input_file, output_file, total_frames, output_text, root, ratio=ratio, xaxis=xaxis, yaxis=yaxis, crf=crf, preset=preset, threads=0)
                return
            
            output_text.see(tk.END)
            
            # Create error summary for dialog
            error_summary = f"GPU encoding failed!\n\nReturn Code: {return_code}\nError: {error_msg}\n\n"
            if len(error_list) > 0:
                error_summary += f"Captured {len(error_list)} error(s):\n"
                for idx, error in enumerate(error_list[:5], 1):  # Show first 5 errors
                    error_summary += f"{idx}. {error[:100]}\n"  # Truncate long errors
                if len(error_list) > 5:
                    error_summary += f"... and {len(error_list) - 5} more errors\n"
            error_summary += "\nCheck the output log for full details."
            
            root.after(100, lambda: messagebox.showerror("Encoding Error", error_summary))
            return
        
        output_text.insert(tk.END, f"\n✅ GPU encoding completed successfully!\n")
        output_text.see(tk.END)
        root.after(SUCCESS_MESSAGE_DELAY, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), root.destroy()))

    except FileNotFoundError:
        error_list.append("FFmpeg not found! Make sure it's installed and added to PATH.")
        output_text.insert(tk.END, "\n❌ Error: FFmpeg not found! Make sure it's installed and added to PATH.\n")
        output_text.insert(tk.END, f"📋 Captured Errors:\n  1. {error_list[0]}\n")
        output_text.see(tk.END)
        messagebox.showerror("Error", "FFmpeg not found! Make sure it's installed and added to PATH.")
    except Exception as e:
        error_list.append(f"Exception: {str(e)}")
        output_text.insert(tk.END, f"\n❌ GPU Encoding Exception: {str(e)}\n")
        output_text.insert(tk.END, f"📋 Captured Errors:\n  1. {error_list[0]}\n")
        output_text.see(tk.END)
        root.after(100, lambda: messagebox.showerror("Encoding Error", f"GPU encoding exception:\n{str(e)}"))


def run_scaling(input_file, output_file, total_frames, output_text, window, ratio, x, y, crf, preset, use_gpu=False, threads=0):
    """Runs the scaling in a separate thread."""
    if use_gpu:
        thread = Thread(target=scale_video_GPU, args=(input_file, output_file, total_frames, output_text, window, ratio, x, y, crf, preset))
    else:
        thread = Thread(target=scale_video_CPU, args=(input_file, output_file, total_frames, output_text, window, ratio, x, y, crf, preset, threads))
    thread.start()


def select_video(output_text, window,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    global WINBOOL

    """Opens file dialog and starts video scaling."""
    file_path = filedialog.askopenfilename(
        title="Select a Video File",
        filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.flv;*.wmv")]
    )

    if file_path:
        # Get performance settings first
        use_gpu, use_all_cores, cpu_cores = get_performance_settings(window, windowBg, buttonBg, activeButtonBg)
        threads = cpu_cores if use_all_cores else 0  # 0 = FFmpeg default (auto)
        
        ratio = get_ratio(window,windowBg, buttonBg, activeButtonBg)
        now = datetime.now()
        
        # Ask user for output folder
        output_folder = filedialog.askdirectory(
            title="Select Output Folder (or Cancel to use same folder as input)",
            initialdir=os.path.dirname(file_path)
        )
        
        if output_folder:
            # Use selected output folder
            input_filename = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(output_folder, f"{input_filename.split('_')[0]}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4")
        else:
            # Use same folder as input
            output_path = os.path.splitext(file_path)[0]
            output_path = f"{output_path.split('_')[0]}_{ratio[1]}_{ratio[4]}_{ratio[5]}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
        
        total_frames = get_total_frames(file_path)
        
        # Display settings info
        encoding_type = "GPU (NVENC)" if use_gpu else "CPU"
        threading_info = f"All cores ({cpu_cores} threads)" if use_all_cores else "Default (auto)"
        output_text.insert(tk.END, f"⚙️ Encoding: {encoding_type} | Threading: {threading_info}\n")
        
        if total_frames:
            output_text.insert(tk.END, f"📂 Selected file: {file_path}\n")
            output_text.insert(tk.END, f"📁 Output file: {output_path}\n")
            output_text.insert(tk.END, f"🎞️ Total frames: {total_frames}\n")
            run_scaling(file_path, output_path, total_frames, output_text, window, ratio[0], ratio[2], ratio[3], ratio[4], ratio[5], use_gpu, threads)
        else:
            output_text.insert(tk.END, "⚠️ Could not determine total frames. Progress wont be displayed.\n")
            output_text.insert(tk.END, f"📂 Selected file: {file_path}\n")
            output_text.insert(tk.END, f"📁 Output file: {output_path}\n")
            output_text.insert(tk.END, f"🎞️ Total frames: {total_frames}\n")
            run_scaling(file_path, output_path, total_frames, output_text, window, ratio[0], ratio[2], ratio[3], ratio[4], ratio[5], use_gpu, threads)
        output_text.see(tk.END)
    else:
        WINBOOL = False


def cancel_operation():
    """Cancel the current video processing operation."""
    global _current_process, _cancel_requested
    _cancel_requested = True
    if _current_process:
        try:
            _current_process.terminate()
            logger.info("FFmpeg process terminated by user")
        except Exception as e:
            logger.error(f"Error terminating process: {e}")

def main(windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    """Creates the Tkinter window."""
    window = tk.Tk()
    window.configure(bg=windowBg)
    window.title(DEFAULT_WINDOW_TITLE)
    window.iconify()

    output_text = tk.Text(window, height=20, width=100, bg=buttonBg, fg="white")
    output_text.pack(pady=10)
    
    # Add cancel button
    cancel_button = tk.Button(window, text="❌ Cancel Operation", command=cancel_operation, 
                              bg=CANCEL_BUTTON_BG, fg="white", font=("Arial", "10", "bold"),
                              activebackground=CANCEL_BUTTON_ACTIVE_BG, activeforeground="white", borderwidth=2)
    cancel_button.pack(pady=5)

    select_video(output_text, window,windowBg, buttonBg, activeButtonBg)

    if WINBOOL:
        window.deiconify()
        window.mainloop()
        messagebox.showinfo("Done", "✅ All videos have been processed!")
        #window.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), window.destroy()))
    else:
        window.destroy()


if __name__ == '__main__':
    main()
