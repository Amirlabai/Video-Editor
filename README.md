# ffmpegMagic

A Python-based GUI wrapper for FFmpeg, designed to simplify video scaling, joining, and processing tasks. Built with `customtkinter` for a modern, responsive interface.

## Features

### Video Scaling
- **Dual Mode Encoding**: Support for both CPU (CRF-based) and GPU (NVENC) encoding.
- **Resolution Control**: Scale videos while maintaining aspect ratio, or force specific dimensions.
- **Manual Orientation**: Double-click files in the list to toggle Horizontal/Vertical orientation (swaps target dimensions).
- **Quality Settings**: Configurable Constant Rate Factor (CRF) and encoding presets.

### Video Tools
- **Video Joining**: Concatenate multiple video files into a single output.
- **Batch Processing**: Queue multiple files for sequential processing.
- **Detailed Info**: View Codec, Duration, Resolution, and File Size in the enhanced file list.

### Modern UI & Automation
- **Progress Tracking**: Real-time progress bar, FPS counter, and time estimates.
- **Settings Management**: Persistent configuration for paths, colors, and hardware preferences.
- **Responsive**: Main window respects Z-order and stays accessible.
- **Console-Free**: Runs silently in the background without popping up annoying console windows.

## Installation

1.  **Prerequisites**:
    -   Python 3.8+
    -   [FFmpeg](https://ffmpeg.org/download.html) installed and added to your system PATH.

2.  **Setup**:
    ```bash
    git clone https://github.com/YourUsername/Video-Editor.git
    cd Video-Editor
    pip install -r requirements.txt
    ```

3.  **Run**:
    ```bash
    python src/VideoScalerInterface.py
    ```

## Development

This project uses **Semantic Versioning** and **GitHub Actions** for automated releases.
-   **Versioning**: Source of truth is `src/_version.py`.
-   **Releases**: Pushing to `main` with Conventional Commits (e.g., `feat:`, `fix:`) triggers a release workflow.

## License
MIT License
