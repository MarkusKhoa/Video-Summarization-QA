from pytube import YouTube
from pydub import AudioSegment
from fastapi import HTTPException
from loguru import logger
from tqdm import tqdm

import yt_dlp
import os

class AudioDownloader:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        self.pbar = None
        os.makedirs(output_dir, exist_ok=True)

    def _on_progress(self, d):
        """Progress bar for download tracking."""
        if d["status"] == "downloading":
            if self.pbar is None:
                self.pbar = tqdm(
                    total=d.get("total_bytes", 0),
                    unit="B",
                    unit_scale=True,
                    desc="Downloading"
                )
            self.pbar.update(d["downloaded_bytes"] - self.pbar.n)
        elif d["status"] == "finished":
            if self.pbar:
                self.pbar.close()
                self.pbar = None

    def download_youtube_video(self, url):
        """Download audio from YouTube video."""
        try:
            # Reset progress bar at the start of each download
            if self.pbar:
                self.pbar.close()
                self.pbar = None

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "%(title)s.%(ext)s",
                "progress_hooks": [self._on_progress],
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }],
                "paths": {"home": self.output_dir}
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'unknown_title')
                file_path = os.path.join(self.output_dir, f"{title}.mp3")
                return file_path, title
        except Exception as e:
            # Ensure progress bar is cleaned up
            if self.pbar:  # Ensure progress bar is closed on error
                self.pbar.close()
                self.pbar = None
            logger.error(f"Download failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    def download_facebook_video(self, url):
        """Download audio from Facebook video."""
        try:
            output_file_path = os.path.join(self.output_dir, "facebook_video.mp3")
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_file_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }]
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return output_file_path
        except Exception as e:
            logger.error(f"Failed to download video from Facebook: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    def extract_audio(self, video_path, output_audio_path=None):
        """Extract audio from video file."""
        try:
            if output_audio_path is None:
                output_audio_path = os.path.join(self.output_dir, "output_audio.mp3")
            
            audio = AudioSegment.from_file(video_path)
            audio.export(output_audio_path, format="mp3")
            return output_audio_path
        except Exception as e:
            logger.error(f"Cannot extract audio from video path: {video_path}")
            raise HTTPException(status_code=400, detail=str(e))

    def get_gcs_destination_path(self, file_path, prefix="audio"):
        """Generate a GCS-friendly path for the audio file."""
        base_name = os.path.basename(file_path)
        return f"{prefix}/{base_name}"


