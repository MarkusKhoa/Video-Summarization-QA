from yt_dlp import YoutubeDL
from pathlib import Path
from tqdm import tqdm
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from pydub.silence import split_on_silence
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint

import re
import os

class VideoAudioDownloader:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        self.audio_file_dict = {}

    def get_safe_filename(self, filename):
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_filename = re.sub(r'_+', '_', safe_filename)
        safe_filename = safe_filename[:50].strip('_')
        return safe_filename

    def download_video(self, url):
        try:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': f'{self.output_folder}/%(title)s.%(ext)s'
            }
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info_dict)
                base, ext = os.path.splitext(filename)
                new_filepath = base + '.mp3'

            self.audio_file_dict[url] = new_filepath
            print(f"Downloaded video {new_filepath} successfully")
            return new_filepath

        except Exception as e:
            print(f"Error downloading video: {e}")
            return None

    def download_many_videos(self, urls):
        for url in tqdm(urls):
            audio_file = self.download_video(url)
            if audio_file:
                self.audio_file_dict[url] = audio_file

class AudioPreprocessor:
    def __init__(self):
        pass


