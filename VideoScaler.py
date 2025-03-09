import sys
import threading
import tkinter as tk
from tkinter import *
from pickle import GLOBAL
from tkinter import filedialog, messagebox
import subprocess
import os
import re
import time
from threading import Thread
from datetime import datetime

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
        if len(output_lines)>2:
            duration_str = output_lines[3]
        else:
            duration_str = output_lines[2]
        fps_str = output_lines[0].split("/")[0]
        return int(int(float(duration_str)) * int(fps_str))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError) as e:
        print(f"Error: {e}")
        return None


def average_list(myList):
    tot = sum(myList)
    return tot / len(myList) if myList else 0


def get_ratio(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    VH_window = tk.Toplevel(root)
    VH_window.configure(bg=windowBg)
    VH_window.title("Choose Orientation")
    #VH_window.transient(root)
    VH_window.grab_set()

    orientation = tk.StringVar(VH_window, value="")
    xaxis = tk.StringVar(VH_window, value="1280")
    yaxis = tk.StringVar(VH_window, value="720")
    crfValue = tk.StringVar(VH_window, value="28")
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
        return False, "_horizontal", "1280", "720", "26", "medium"
    else:
        return selected.get(), orientation.get(), xaxis.get(), yaxis.get(),crfValue.get(), preset.get()


def get_pixel(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    VH_window = tk.Toplevel(root)
    VH_window.configure(bg=windowBg)
    VH_window.title("Choose pixels")
    #VH_window.transient(root)
    VH_window.grab_set()

    x = tk.IntVar(VH_window, value=1280)
    y = tk.IntVar(VH_window, value=720) 
    selected = tk.BooleanVar(VH_window)

    def set_hd():
        selected.set(False)
        VH_window.destroy()

    def set_fhd():
        selected.set(True)
        x.set(1920)
        y.set(1080)
        VH_window.destroy()

    def set_4k():
        selected.set(True)
        x.set(3840)
        y.set(2160)
        VH_window.destroy()

    label = tk.Label(VH_window, text="Video Resolution", bg=windowBg, fg="white", font=("Arial", "16", "bold"))
    label.grid(row=0, column=0, columnspan=2)

    horizontal_button = tk.Button(VH_window, text="HD:1280x720", command=set_hd, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    horizontal_button.grid(row=1, column=0, pady=10, padx=5)

    vertical_button = tk.Button(VH_window, text="FHD:1920x1080", command=set_fhd, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.grid(row=1, column=1, pady=10, padx=5)

    vertical_button = tk.Button(VH_window, text="FHD:4k", command=set_4k, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.grid(row=1, column=2, pady=10, padx=5)

    VH_window.wait_window()

    # If closed without selection
    if not selected.get():
        return x.get(), y.get()
    else:
        return x.get(), y.get()


def get_crf(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    VH_window = tk.Toplevel(root)
    VH_window.configure(bg=windowBg)
    VH_window.title("Choose lossless range")
    #VH_window.transient(root)
    VH_window.grab_set()

    crf = tk.StringVar(VH_window,value="")

    def set_crf():
        crf.set(str(int(horizontal_slider.get())))
        VH_window.destroy()

    label = tk.Label(VH_window, text="Video Encoding", bg=windowBg, fg="white", font=("Arial", "16", "bold"))
    label.pack(padx=10,pady=5)
    label_2 = tk.Label(VH_window, text="the lower the better", bg=windowBg, fg="white", font=("Arial", "10", "bold"))
    label_2.pack(padx=10,pady=5)

    horizontal_slider = tk.Scale(VH_window, from_=17, to=30, orient=HORIZONTAL, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                                 activebackground=activeButtonBg, borderwidth=2)
    horizontal_slider.pack(padx=10,pady=5)
    horizontal_slider.set(26)

    vertical_button = tk.Button(VH_window, text="Set", command=set_crf, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    vertical_button.pack(padx=10,pady=5)

    VH_window.wait_window()

    # If closed without selection
    if not crf == "":
        return "26"
    else:
        return crf.get()


def get_preset(root,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    gp_window = tk.Toplevel(root)
    gp_window.configure(bg=windowBg)
    gp_window.title("Choose preset")
    #VH_window.transient(root)
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


def scale_video(input_file, output_file, total_frames, output_text, root,ratio=False, xaxis="1280", yaxis="720",crf="26",preset="medium"):

    if ratio:
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", f"scale={yaxis}:{xaxis}",
            "-c:v", "libx264", "-crf", crf, "-preset", preset,
            "-c:a", "aac", "-b:a", "128k",
            "-progress", "pipe:1", "-nostats",
            output_file
        ]
    else:
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", f"scale={xaxis}:{yaxis}",
            "-c:v", "libx264", "-crf", crf, "-preset", preset,
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

        #root.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), root.destroy()))

    except FileNotFoundError:
        messagebox.showerror("Error", "FFmpeg not found! Make sure it's installed and added to PATH.")


def run_scaling(input_file, output_file, total_frames, output_text, window,ratio,x,y,crf,preset):
    """Runs the scaling in a separate thread."""
    thread = Thread(target=scale_video, args=(input_file, output_file, total_frames, output_text, window,ratio,x,y,crf,preset))
    thread.start()


def select_video(output_text, window,windowBg = '#1e1e1e', buttonBg = '#323232', activeButtonBg = '#192332'):
    global WINBOLL

    """Opens file dialog and starts video scaling."""
    file_path = filedialog.askopenfilename(
        title="Select a Video File",
        filetypes=[("Video Files", "*.mp4;*.mkv;*.avi;*.mov;*.flv;*.wmv")]
    )

    if file_path:
        ratio = get_ratio(window,windowBg, buttonBg, activeButtonBg)
        #ratio= [True,'hozi']
        #print(ratio)
        #pixel = get_pixel(window,windowBg, buttonBg, activeButtonBg)
        #pixel = [1280,720]
        now = datetime.now()
        output_path = os.path.splitext(file_path)[0]
        output_path = f"{output_path.split('_')[0]}_scaled_{now.strftime('%Y%m%d_%H%M%S')}{ratio[1]}.mp4"
        total_frames = get_total_frames(file_path)
        if total_frames:
            output_text.insert(tk.END, f"📂 Selected file: {file_path}\n")
            output_text.insert(tk.END, f"📁 Output file: {output_path}\n")
            output_text.insert(tk.END, f"🎞️ Total frames: {total_frames}\n")
            run_scaling(file_path, output_path, total_frames, output_text, window,ratio[0],ratio[2],ratio[3],ratio[4],ratio[5])
        else:
            output_text.insert(tk.END, "⚠️ Could not determine total frames. Progress wont be displayed.\n")
            output_text.insert(tk.END, f"📂 Selected file: {file_path}\n")
            output_text.insert(tk.END, f"📁 Output file: {output_path}\n")
            output_text.insert(tk.END, f"🎞️ Total frames: {total_frames}\n")
            run_scaling(file_path, output_path, total_frames, output_text, window,ratio[0],ratio[2],ratio[3],ratio[4],ratio[5])
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

    select_video(output_text, window,windowBg, buttonBg, activeButtonBg)

    if WINBOLL:
        window.deiconify()
        window.mainloop()
        messagebox.showinfo("Done", "✅ All videos have been processed!")
        #window.after(1000, lambda: (messagebox.showinfo("Done", "✅ All videos have been processed!"), window.destroy()))
    else:
        window.destroy()


if __name__ == '__main__':
    main()
