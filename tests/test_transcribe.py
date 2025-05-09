from faster_whisper import WhisperModel
from dotenv import load_dotenv
from loguru import logger
from tqdm import tqdm

import whisper
import os
import time

filepath = 'data/Tập 56 ｜ Án Trong Án - Kẻ Máu Lạnh Nhiều Tiền Tuyên Bố Diệt Cả Thẩm Phán - Tra Án Special.mp3'

model = WhisperModel(
    model_size_or_path='models/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120',
    device="cpu",
    compute_type="float32",
    download_root="models",
    local_files_only=True
)

def transcribe_audio(audio_file, model):
    segments, info = model.transcribe(
        audio_file,
        beam_size = 5,
        vad_filter=True,
        word_timestamps=True
    )

    segments_list = list(segments)

    with tqdm(segments_list, desc="Transcribing") as pbar:
        transcript = ""
        for segment in pbar:
            logger.info(f"Segment: {segment.text}")
            transcript += f"{segment.text}\n"
            pbar.set_postfix({"Time": f"{segment.start:.2f}s"})
    
    return transcript

transcript = transcribe_audio(audio_file=filepath, model=model)
logger.info(f"Transcript: {transcript}")

with open("data/sample_transcript_Tra_an.txt", "w") as f:
    f.write(transcript)