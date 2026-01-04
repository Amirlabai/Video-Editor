from models.ui.Windows import VideoScalerWindow, BatchWindow, JoinWindow
from models.ui.UnifiedProcessingWindow import UnifiedProcessingWindow
from models.ConfigManager import get_config_manager
from tkinter import messagebox

import customtkinter as ctk
import platform
import sys
import os


def resource_path(relative_path):
	""" Get absolute path to resource, works for dev and for Nuitka/PyInstaller """
	try:
		# Nuitka/PyInstaller creates a temp folder and stores path in sys._MEIPASS
		# However, for data files meant to be alongside the exe, we use sys.executable
		if getattr(sys, 'frozen', False):
			# If the application is run as a bundle/frozen executable
			base_path = os.path.dirname(sys.executable)
			base_path = os.path.join(base_path,'_internal')
		else:
			# If running as a normal script
			base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

		full_path = os.path.join(base_path, relative_path)
		return full_path
	except Exception as e:
		return os.path.join(os.path.abspath("."), relative_path)

ctk.set_default_color_theme(resource_path("assets/custom-theme.json"))

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
        window = UnifiedProcessingWindow(windowBg, buttonBg, activeButtonBg)
        window.run()

    def batch_scale():
        window = UnifiedProcessingWindow(windowBg, buttonBg, activeButtonBg)
        window.run()

    def join_videos():
        window = JoinWindow(windowBg, buttonBg, activeButtonBg)
        window.run()

    def show_settings():
        """Show settings/preferences dialog."""
        config = get_config_manager()
        settings_window = ctk.CTkToplevel(root)
        settings_window.title("Settings & Configuration")
        settings_window.geometry("600x700+50+50")
        settings_window.grab_set()
        
        # Title
        title_label = ctk.CTkLabel(settings_window, text="⚙️ Settings & Configuration", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=10)
        
        # Config file location
        config_path = config.get_config_file_path()
        path_frame = ctk.CTkFrame(settings_window)
        path_frame.pack(pady=10, padx=20, fill="x")
        
        path_label = ctk.CTkLabel(path_frame, text="Configuration File:")
        path_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        path_text = ctk.CTkTextbox(path_frame, height=50)
        path_text.insert("1.0", config_path)
        path_text.configure(state="disabled")
        path_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
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
        
        open_file_btn = ctk.CTkButton(buttons_frame, text="Open Config File", command=open_config_file)
        open_file_btn.pack(side="left", padx=5)
        
        open_folder_btn = ctk.CTkButton(buttons_frame, text="Open Config Folder", command=open_config_folder)
        open_folder_btn.pack(side="left", padx=5)
        
        copy_path_btn = ctk.CTkButton(buttons_frame, text="Copy Path", command=copy_path)
        copy_path_btn.pack(side="left", padx=5)
        
        # Current settings display
        settings_frame = ctk.CTkFrame(settings_window)
        settings_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        settings_label = ctk.CTkLabel(settings_frame, text="Current Settings:")
        settings_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Get current settings
        use_gpu, use_all_cores = config.get_performance_settings()
        default_crf, default_preset, default_resolution = config.get_encoding_settings()
        
        settings_text = ctk.CTkTextbox(settings_frame, height=200)
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
        settings_text.configure(state="disabled")
        settings_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Close button
        close_btn = ctk.CTkButton(settings_window, text="Close", command=settings_window.destroy)
        close_btn.pack(pady=10)

    root = ctk.CTk()  # Create CTk window

    # Set minimum width and height
    root.minsize(width=300, height=200)
    root.geometry("600x200+50+50")
    root.title("ffmpegMagic")
    try:
        icon_path = resource_path("assets/ffmpegMagic.ico")
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Error setting icon: {e}")

    # CustomTkinter window elements
    categories_label = ctk.CTkLabel(root, text="Video Editor", font=ctk.CTkFont(size=16, weight="bold"))
    categories_label.pack(pady=5)

    button_frame = ctk.CTkFrame(root, fg_color="transparent")
    button_frame.pack(pady=(10, 5))

    scaleVideo = ctk.CTkButton(button_frame, text="Scale Down A video", command=scale_video)
    batchScale = ctk.CTkButton(button_frame, text="Scale Down Videos in a folder", command=batch_scale, width=200)
    joinVideos = ctk.CTkButton(button_frame, text="Combine Videos", command=join_videos)

    scaleVideo.pack(side="left", padx=5)
    batchScale.pack(side="left", padx=5)
    joinVideos.pack(side="left", padx=5)

    # Settings button
    settings_button = ctk.CTkButton(root, text="⚙️ Settings", command=show_settings)
    settings_button.pack(pady=5)

    # Close button with custom color
    close_button = ctk.CTkButton(root, 
                                text="Close Program", 
                                command=close_program,
                                fg_color=get_rgb((200,30,30)), 
                                hover_color=get_rgb((100,50,50)),
    )
    close_button.pack(side="bottom", fill="x", pady=(5, 10), padx=10)
    
    root.protocol("WM_DELETE_WINDOW", close_program)
    
    root.mainloop()

def main():
    window()

if __name__ == "__main__":
    main()
