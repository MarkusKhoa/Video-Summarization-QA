from pytube import YouTube
from pytube.cli import on_progress
from pydub import AudioSegment
from fastapi import HTTPException
from loguru import logger
from tqdm import tqdm

import requests
import yt_dlp
import os

def download_youtube_video(url, output_dir="data"):
   try:
       # Create output directory if it doesn't exist
       os.makedirs(output_dir, exist_ok=True)
       
       ydl_opts = {
           "format": "bestaudio/best",
           "outtmpl": "%(title)s.%(ext)s",  # Use video title as filename
           "progress_hooks": [on_progress],
           "postprocessors": [{
               "key": "FFmpegExtractAudio",
               "preferredcodec": "mp3",
           }],
           "paths": {"home": output_dir}  # Set output directory
       }
       
       with yt_dlp.YoutubeDL(ydl_opts) as ydl:
           info = ydl.extract_info(url, download=True)
           title = info.get('title', 'unknown_title')
           return os.path.join(output_dir, f"{title}.mp3"), title
   except Exception as e:
       logger.error(f"Download failed: {str(e)}")
       raise HTTPException(status_code=400, detail=str(e))


def on_progress(d):
    if d["status"] == "downloading":
        if not hasattr(on_progress, "pbar"):
            on_progress.pbar = tqdm(total = d.get("total_bytes", 0), unit = "B",
                                    unit_scale = True, desc = "Downloading")
        on_progress.pbar.update(d["downloaded_bytes"] - on_progress.pbar.n)
    elif d["status"] == "finished":
        if hasattr(on_progress, "pbar"):
            on_progress.pbar.close()    
        

def download_facebook_video(url, output_file_path):
    try:
        ydl_opts = {'outtmpl': 'downloaded_video.%(ext)s'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_file_path
    except:
        raise HTTPException(status_code=400, detail=f"Failed to download video from this URL: {url}")


def extract_audio(video_path, output_audio_path = "output_audio.mp3"):
    try:
        audio = AudioSegment.from_file(video_path)
        audio.export(output_audio_path, format="mp3")
        return output_audio_path
    except:
        logger.error(f"Cannot extract audio from video path: {video_path}")

if __name__ == "__main__":
    yt_url = "https://www.youtube.com/watch?v=3Jhtj0k7SOk"
    fb_url = "https://www.facebook.com/watch?v=1534519627339156"

    yt_video_path, title = download_youtube_video(url = yt_url, output_dir = "data")
    
