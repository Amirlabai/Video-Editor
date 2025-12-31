import tkinter as tk
from tkinter import messagebox, scrolledtext
import os
import platform

# Use new class-based UI components
try:
    from models.ui.Windows import VideoScalerWindow, BatchWindow, JoinWindow
except ImportError:
    # Fallback to old imports if new classes aren't available
    import models.VideoScaler as VideoScaler
    import models.ProcessFolder as ProcessFolder
    import models.JoinFiles as JoinFiles
    VideoScalerWindow = None
    BatchWindow = None
    JoinWindow = None

from models.ConfigManager import get_config_manager

def get_rgb(rgb):
    """translates an rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb

def window():
    # Load UI colors from config
    config = get_config_manager()
    windowBg, buttonBg, activeButtonBg = config.get_ui_colors()

    def close_program():
        root.destroy()
        root.quit()

    def scale_video():
        if VideoScalerWindow:
            window = VideoScalerWindow(windowBg, buttonBg, activeButtonBg)
            window.run()
        else:
            VideoScaler.main(windowBg, buttonBg, activeButtonBg)

    def batch_scale():
        if BatchWindow:
            window = BatchWindow(windowBg, buttonBg, activeButtonBg)
            window.run()
        else:
            ProcessFolder.main(windowBg, buttonBg, activeButtonBg)

    def join_videos():
        if JoinWindow:
            window = JoinWindow(windowBg, buttonBg, activeButtonBg)
            window.run()
        else:
            JoinFiles.main(windowBg, buttonBg, activeButtonBg)

    def show_settings():
        """Show settings/preferences dialog."""
        config = get_config_manager()
        settings_window = tk.Toplevel(root)
        settings_window.configure(bg=windowBg)
        settings_window.title("Settings & Configuration")
        settings_window.geometry("600x500")
        settings_window.grab_set()
        
        # Title
        title_label = tk.Label(settings_window, text="⚙️ Settings & Configuration", 
                               bg=windowBg, fg="white", font=("Arial", "16", "bold"))
        title_label.pack(pady=10)
        
        # Config file location
        config_path = config.get_config_file_path()
        path_frame = tk.Frame(settings_window, bg=windowBg)
        path_frame.pack(pady=10, padx=20, fill="x")
        
        path_label = tk.Label(path_frame, text="Configuration File:", 
                              bg=windowBg, fg="white", font=("Arial", "10", "bold"))
        path_label.pack(anchor="w")
        
        path_text = tk.Text(path_frame, height=2, bg=buttonBg, fg="white", 
                           font=("Arial", "9"), wrap=tk.WORD, relief=tk.FLAT)
        path_text.insert("1.0", config_path)
        path_text.config(state=tk.DISABLED)
        path_text.pack(fill="x", pady=5)
        
        # Buttons frame
        buttons_frame = tk.Frame(settings_window, bg=windowBg)
        buttons_frame.pack(pady=10)
        
        def open_config_file():
            """Open config file in default editor."""
            if config.open_config_in_editor():
                messagebox.showinfo("Success", "Configuration file opened in your default text editor.")
            else:
                messagebox.showerror("Error", "Could not open configuration file.\n\nYou can manually edit it at:\n" + config_path)
        
        def open_config_folder():
            """Open config folder in file explorer."""
            config_dir = config.get_config_dir_path()
            try:
                if platform.system() == 'Windows':
                    os.startfile(config_dir)
                elif platform.system() == 'Darwin':  # macOS
                    os.system(f'open "{config_dir}"')
                else:  # Linux
                    os.system(f'xdg-open "{config_dir}"')
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder:\n{str(e)}")
        
        def copy_path():
            """Copy config path to clipboard."""
            root.clipboard_clear()
            root.clipboard_append(config_path)
            messagebox.showinfo("Copied", "Configuration file path copied to clipboard!")
        
        open_file_btn = tk.Button(buttons_frame, text="📝 Open Config File", command=open_config_file,
                                  bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                                  activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
        open_file_btn.pack(side="left", padx=5)
        
        open_folder_btn = tk.Button(buttons_frame, text="📂 Open Config Folder", command=open_config_folder,
                                    bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                                    activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
        open_folder_btn.pack(side="left", padx=5)
        
        copy_path_btn = tk.Button(buttons_frame, text="📋 Copy Path", command=copy_path,
                                  bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                                  activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
        copy_path_btn.pack(side="left", padx=5)
        
        # Current settings display
        settings_frame = tk.Frame(settings_window, bg=windowBg)
        settings_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        settings_label = tk.Label(settings_frame, text="Current Settings:", 
                                  bg=windowBg, fg="white", font=("Arial", "10", "bold"))
        settings_label.pack(anchor="w")
        
        # Get current settings
        use_gpu, use_all_cores = config.get_performance_settings()
        default_crf, default_preset, default_resolution = config.get_encoding_settings()
        
        settings_text = scrolledtext.ScrolledText(settings_frame, height=12, bg=buttonBg, fg="white",
                                                  font=("Courier", "9"), wrap=tk.WORD, relief=tk.FLAT)
        settings_text.insert("1.0", f"""Performance Settings:
  • Use GPU: {use_gpu}
  • Use All CPU Cores: {use_all_cores}

Encoding Defaults:
  • Default CRF: {default_crf}
  • Default Preset: {default_preset}
  • Default Resolution: {default_resolution}

Last Used Folders:
  • Input Folder: {config.get_last_input_folder() or "(none)"}
  • Output Folder: {config.get_last_output_folder() or "(none)"}
  • Join Input Folder: {config.get_last_join_input_folder() or "(none)"}
  • Join Output Folder: {config.get_last_join_output_folder() or "(none)"}

Note: Settings are automatically saved when you use the application.
You can manually edit the JSON config file for advanced customization.""")
        settings_text.config(state=tk.DISABLED)
        settings_text.pack(fill="both", expand=True, pady=5)
        
        # Close button
        close_btn = tk.Button(settings_window, text="Close", command=settings_window.destroy,
                             bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                             activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
        close_btn.pack(pady=10)

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

    # Settings button
    settings_button = tk.Button(root, text="⚙️ Settings", command=show_settings, 
                               bg=buttonBg, fg="white", font=("Arial", "10", "bold"),
                               activebackground=activeButtonBg, activeforeground="white", borderwidth=2)
    settings_button.pack(pady=5)

    close_button = tk.Button(root, text="Close Program", command=close_program, bg=get_rgb((200,30,30)), fg="white", font=("Arial", "10", "bold"),
                           activebackground=get_rgb((100,50,50)), activeforeground="white", borderwidth=2)
    close_button.pack(side="bottom", fill="x", pady=(5, 10), padx=10)
    
    root.protocol("WM_DELETE_WINDOW", close_program)
    
    root.mainloop()

def main():
    window()

if __name__ == "__main__":
    main()
