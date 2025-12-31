"""
Constants for Video Editor application.
Contains default values, resolutions, and configuration settings.
"""

# Video Resolutions
HD_WIDTH = 1280
HD_HEIGHT = 720
FHD_WIDTH = 1920
FHD_HEIGHT = 1080
UHD_4K_WIDTH = 3840
UHD_4K_HEIGHT = 2160

# Resolution tuples for easy access
HD_RESOLUTION = (HD_WIDTH, HD_HEIGHT)
FHD_RESOLUTION = (FHD_WIDTH, FHD_HEIGHT)
UHD_4K_RESOLUTION = (UHD_4K_WIDTH, UHD_4K_HEIGHT)

# Encoding Quality (CRF/CQ values)
# Lower = better quality, larger file size
# Higher = lower quality, smaller file size
DEFAULT_CRF = "26"
HIGH_QUALITY_CRF = "23"
MEDIUM_QUALITY_CRF = "26"
LOW_QUALITY_CRF = "28"
CRF_MIN = 17
CRF_MAX = 30

# Encoding Presets
# Slower = better compression, takes longer
# Faster = less compression, faster encoding
DEFAULT_PRESET = "medium"
PRESET_OPTIONS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

# Audio Settings
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "128k"

# Video Codecs
CPU_CODEC = "libx264"
GPU_CODEC = "h264_nvenc"

# Supported Video Formats
SUPPORTED_VIDEO_FORMATS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")

# UI Colors (default dark theme)
DEFAULT_WINDOW_BG = '#1e1e1e'
DEFAULT_BUTTON_BG = '#323232'
DEFAULT_ACTIVE_BUTTON_BG = '#192332'
CANCEL_BUTTON_BG = '#d32f2f'
CANCEL_BUTTON_ACTIVE_BG = '#b71c1c'

# Window Settings
DEFAULT_WINDOW_TITLE = "Video Scaler"
BATCH_WINDOW_TITLE = "Folder Video Scaler"
JOINER_WINDOW_TITLE = "Video Joiner"

# Progress Tracking
PROGRESS_UPDATE_INTERVAL = 5  # Update progress every N frames
AVG_FRAME_BUFFER_SIZE = 50
AVG_TIME_BUFFER_SIZE = 50

# File Naming
OUTPUT_FILENAME_FORMAT = "{base}_{ratio}_{crf}_{preset}_{timestamp}.mp4"
JOINED_OUTPUT_FILENAME = "joined_output.mp4"
CONCAT_LIST_FILENAME = "concat_list.txt"

# Timeouts and Delays
PROCESS_TERMINATION_TIMEOUT = 5  # seconds
CANCELLATION_MESSAGE_DELAY = 2000  # milliseconds
SUCCESS_MESSAGE_DELAY = 1000  # milliseconds

# Logging
LOG_DIR_NAME = ".video_editor"
LOG_FILENAME = "video_editor.log"

# Configuration
CONFIG_DIR_NAME = ".video_editor"
CONFIG_FILENAME = "config.json"

