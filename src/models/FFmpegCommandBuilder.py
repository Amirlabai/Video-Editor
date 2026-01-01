"""
FFmpegCommandBuilder class for constructing FFmpeg commands.
"""

from typing import List, Optional
from .constants import (
    HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT, UHD_4K_WIDTH, UHD_4K_HEIGHT,
    DEFAULT_CRF, DEFAULT_PRESET, DEFAULT_AUDIO_CODEC, DEFAULT_AUDIO_BITRATE,
    CPU_CODEC, GPU_CODEC
)


class FFmpegCommandBuilder:
    """Builds FFmpeg commands for video processing operations."""
    
    @staticmethod
    def build_scale_command_cpu(
        input_file: str,
        output_file: str,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET,
        threads: int = 0,
        video_codec: str = CPU_CODEC,
        audio_codec: str = DEFAULT_AUDIO_CODEC,
        audio_bitrate: str = DEFAULT_AUDIO_BITRATE
    ) -> List[str]:
        """Build FFmpeg command for CPU-based video scaling.
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor (quality setting)
            preset: Encoding preset
            threads: Number of threads (0 = auto)
            
        Returns:
            List of command arguments
        """
        cmd = [
            "ffmpeg", "-i", input_file,
            "-vf", f"scale={xaxis}:{yaxis}",
            "-c:v", video_codec,
            "-crf", crf,
            "-preset", preset,
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-progress", "pipe:1",
            "-nostats",
            "-y",  # Overwrite output file
            output_file
        ]
        
        if threads > 0:
            # Insert threads parameter after codec
            cmd.insert(cmd.index("-c:v") + 2, "-threads")
            cmd.insert(cmd.index("-threads") + 1, str(threads))
        
        return cmd
    
    @staticmethod
    def build_scale_command_gpu(
        input_file: str,
        output_file: str,
        xaxis: str = str(HD_WIDTH),
        yaxis: str = str(HD_HEIGHT),
        crf: str = DEFAULT_CRF,
        preset: str = DEFAULT_PRESET,
        video_codec: str = GPU_CODEC,
        audio_codec: str = DEFAULT_AUDIO_CODEC,
        audio_bitrate: str = DEFAULT_AUDIO_BITRATE
    ) -> List[str]:
        """Build FFmpeg command for GPU-based video scaling (NVENC).
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            xaxis: Output width
            yaxis: Output height
            crf: Constant Rate Factor (quality setting)
            preset: Encoding preset
            
        Returns:
            List of command arguments
        """
        # Use scale_cuda for NVENC codecs, regular scale for others
        if "nvenc" in video_codec:
            scale_filter = f"scale_cuda={xaxis}:{yaxis}"
        else:
            scale_filter = f"scale={xaxis}:{yaxis}"
        
        return [
            "ffmpeg", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda",
            "-i", input_file,
            "-vf", scale_filter,
            "-c:v", video_codec,
            "-cq", crf,
            "-preset", preset,
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-progress", "pipe:1",
            "-nostats",
            "-y",  # Overwrite output file
            output_file
        ]
    
    @staticmethod
    def build_concat_command(concat_file: str, output_file: str) -> List[str]:
        """Build FFmpeg command for joining videos using concat demuxer.
        
        Args:
            concat_file: Path to concat list file
            output_file: Output video file path
            
        Returns:
            List of command arguments
        """
        return [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c", "copy",
            "-progress", "pipe:1",
            "-nostats",
            "-y",  # Overwrite output file
            output_file
        ]

