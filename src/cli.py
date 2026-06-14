import os
import sys
import argparse
import shutil
import time
from datetime import datetime
from pathlib import Path
from models.VideoProcessor import VideoProcessor
from models.VideoJoiner import VideoJoiner
from models.ConfigManager import get_config_manager
from models.VideoInfo import VideoInfo
from models.progress_reporter import PrintProgressReporter
from models.constants import HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT, UHD_4K_WIDTH, UHD_4K_HEIGHT

# Absolute paths relative to the script location
SCRIPT_DIR = Path(__file__).parent.parent.absolute()
INCOMING_DIR = SCRIPT_DIR / ".incoming"
OUTPUT_DIR = SCRIPT_DIR / "output"

def get_resolution(res_name):
    resolutions = {
        "HD": (str(HD_WIDTH), str(HD_HEIGHT)),
        "FHD": (str(FHD_WIDTH), str(FHD_HEIGHT)),
        "4K": (str(UHD_4K_WIDTH), str(UHD_4K_HEIGHT))
    }
    return resolutions.get(res_name.upper(), resolutions["FHD"])

def create_action_dir(action_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    action_dir = OUTPUT_DIR / f"{action_name}_{timestamp}"
    action_dir.mkdir(parents=True, exist_ok=True)
    orig_dir = action_dir / "original_files"
    orig_dir.mkdir(exist_ok=True)
    return action_dir, orig_dir

def list_incoming():
    if not INCOMING_DIR.exists():
        print(f"Error: {INCOMING_DIR} directory not found.")
        return
    
    files = list(INCOMING_DIR.glob("*"))
    if not files:
        print(f"No files in {INCOMING_DIR}/")
        return
    
    print(f"Files in {INCOMING_DIR}/:")
    for f in files:
        if f.is_file():
            size = os.path.getsize(f)
            print(f"  - {f.name} ({VideoProcessor.format_file_size(size)})")

def compress(args):
    config = get_config_manager()
    processor = VideoProcessor()
    reporter = PrintProgressReporter()
    
    action_dir, orig_dir = create_action_dir("compress")
    
    files_to_process = []
    if args.file:
        files_to_process.append(INCOMING_DIR / args.file)
    else:
        files_to_process = [f for f in INCOMING_DIR.glob("*") if f.is_file()]
    
    if not files_to_process:
        print("No files to process.")
        return

    # Encoding settings
    def_crf, def_preset, def_res = config.get_encoding_settings()
    crf = args.crf or def_crf
    preset = args.preset or def_preset
    res_name = args.resolution or def_res
    width, height = get_resolution(res_name)
    
    use_gpu, use_all_cores = config.get_performance_settings()
    if args.gpu is not None:
        use_gpu = args.gpu
    
    print(f"Processing {len(files_to_process)} files...")
    print(f"Settings: Resolution={res_name} ({width}x{height}), CRF={crf}, Preset={preset}, GPU={use_gpu}")
    print(f"Results will be in: {action_dir}")
    
    for input_path in files_to_process:
        if not input_path.exists():
            print(f"File not found: {input_path}")
            continue
            
        output_path = action_dir / f"compressed_{input_path.name}"
        
        print(f"\nCompressing: {input_path.name} -> {output_path.name}")
        
        vi = VideoInfo(str(input_path))
        total_frames = vi.get_total_frames()
        duration = vi.get_duration()
        fps = vi.fps
        
        success = False
        if use_gpu:
            processor.scale_video_gpu(
                str(input_path), str(output_path),
                total_frames=total_frames,
                reporter=reporter,
                xaxis=width, yaxis=height,
                crf=crf, preset=preset,
                input_duration=duration, input_fps=fps
            )
            success = os.path.exists(output_path)
        else:
            processor.scale_video_cpu(
                str(input_path), str(output_path),
                total_frames=total_frames,
                reporter=reporter,
                xaxis=width, yaxis=height,
                crf=crf, preset=preset,
                input_duration=duration, input_fps=fps
            )
            success = os.path.exists(output_path)
            
        if success:
            print(f"Moving {input_path.name} to original_files/")
            shutil.move(str(input_path), str(orig_dir / input_path.name))

def join_videos(args):
    config = get_config_manager()
    joiner = VideoJoiner()
    video_info = VideoInfo()
    
    action_dir, orig_dir = create_action_dir("join")
    
    video_files = joiner.get_video_files(str(INCOMING_DIR))
    total_files = len(video_files)
    
    if total_files < 2:
        print("Need at least two compatible videos to join.")
        return
    
    print(f"Found {total_files} video files to join.")
    print(f"Results will be in: {action_dir}")
    
    # Check compatibility
    if not video_info.check_compatibility(video_files):
        print("Error: Videos have different properties and can't be joined.")
        return
    
    # Create concat file in .incoming
    concat_file = joiner.create_concat_file(video_files, str(INCOMING_DIR))
    
    from models.constants import JOINED_OUTPUT_FILENAME
    output_file = str(action_dir / JOINED_OUTPUT_FILENAME)
    
    print(f"Joining videos into: {output_file}")
    joiner.join_videos(concat_file, output_file, total_files, reporter=PrintProgressReporter())
    
    # Clean up concat file
    if os.path.exists(concat_file):
        os.remove(concat_file)
        
    if os.path.exists(output_file):
        print("Moving original files to original_files/")
        for f in video_files:
            f_path = Path(f)
            shutil.move(str(f_path), str(orig_dir / f_path.name))

def main():
    parser = argparse.ArgumentParser(description="ffmpegMagic CLI - Agentic Video Processing")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List command
    subparsers.add_parser("list", help="List files in .incoming/")
    
    # Compress command
    comp_parser = subparsers.add_parser("compress", help="Compress videos in .incoming/")
    comp_parser.add_argument("--file", help="Specific file in .incoming/ to process")
    comp_parser.add_argument("--crf", help="CRF value (lower = better quality)")
    comp_parser.add_argument("--preset", help="Encoding preset (slower = better compression)")
    comp_parser.add_argument("--resolution", choices=["HD", "FHD", "4K"], help="Output resolution")
    comp_parser.add_argument("--gpu", action="store_true", default=None, help="Force GPU encoding")
    comp_parser.add_argument("--cpu", action="store_false", dest="gpu", help="Force CPU encoding")
    
    # Join command
    subparsers.add_parser("join", help="Join videos in .incoming/ into one file")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_incoming()
    elif args.command == "compress":
        compress(args)
    elif args.command == "join":
        join_videos(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
