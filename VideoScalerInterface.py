import tkinter as tk
from tkinter import messagebox

import VideoScaler
import ProcessFolder

def get_rgb(rgb):
    """translates an rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb

def window():

    windowBg = get_rgb((30,30,30))
    buttonBg = get_rgb((50,50,50))
    activeButtonBg = get_rgb((25,35,50))

    def close_program():
        root.destroy()
        root.quit()

    def scale_video():
        VideoScaler.main(windowBg, buttonBg, activeButtonBg)

    def batch_scale():
        ProcessFolder.main(windowBg, buttonBg, activeButtonBg)

    def join_videos():
        messagebox.showerror("Error", "haven't made that one yet :(")



    root = tk.Tk()  # Create Tk window
    root.configure(bg=windowBg)  # Set background color to black

    # Set minimum width and height
    root.minsize(width=300, height=200)  # Adjust values as needed

    root.title("ffmpegMagic")

    # Tkinter window elements
    categories_label = tk.Label(root, text="video editor", bg=windowBg, fg="white", font=("Arial", "16", "bold"))
    categories_label.pack(pady=5)

    button_frame = tk.Frame(root, bg= windowBg, borderwidth=0, relief="solid", highlightbackground="white", highlightthickness=0)
    button_frame.pack(pady=(10, 5))

    scaleVideo = tk.Button(button_frame, text="Scale Down A video", command=scale_video, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    batchScale = tk.Button(button_frame, text="Scale Down Videos in a folder", command=batch_scale, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    joinVideos = tk.Button(button_frame, text="combine videos", command=join_videos, bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                           activebackground=activeButtonBg, activeforeground="white", borderwidth=2) # Added outline

    scaleVideo.pack(side="left", padx=5)
    batchScale.pack(side="left", padx=5)
    joinVideos.pack(side="left", padx=5)

    close_button = tk.Button(root, text="Close Program", command=close_program, bg=get_rgb((200,30,30)), fg="white", font=("Arial", "10", "bold"),
                           activebackground=get_rgb((100,50,50)), activeforeground="white", borderwidth=2)
    close_button.pack(side="bottom", fill="x", pady=(5, 10), padx=10)

    root.mainloop()

def main():
    window()

if __name__ == "__main__":
    main()