from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from fastapi import FastAPI, UploadFile, HTTPException, Form
from typing import List
from tenacity import retry, stop_after_attempt, wait_fixed
from google.cloud import storage
from .audio_processing import AudioDownloader  # Changed to relative import

import re
import os
import io

app = FastAPI()

class AudioPipeline:
    def __init__(self, preprocessor, inference_client, gcs_bucket_name):
        self.preprocessor = preprocessor
        self.inference_client = inference_client
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.gcs_bucket_name = gcs_bucket_name
        self.gcs_client = storage.Client()
        self.downloader = AudioDownloader(output_dir="temp_downloads")

    def upload_to_gcs(self, file_path, destination_blob_name):
        """Upload a file to Google Cloud Storage."""
        try:
            bucket = self.gcs_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(file_path)
            logger.info(f"Uploaded {file_path} to GCS bucket {self.gcs_bucket_name} as {destination_blob_name}")
        except Exception as e:
            logger.error(f"Failed to upload {file_path} to GCS: {str(e)}")
            raise

    def transcribe_file(self, audio_file):
        """Process a single audio file."""
        try:
            # Step 1: Convert audio
            logger.info(f"Converting audio file: {audio_file}")
            audio = self.preprocessor.convert_audio(audio_file)
            
            # Step 2: Split into chunks
            logger.info("Splitting audio into chunks")
            chunks = self.preprocessor.chunk_audio(audio)
            
            # Step 3: Run inference
            logger.info(f"Running inference on {len(chunks)} chunks")
            transcriptions = self.inference_client.process_batch(chunks)
            
            # Step 4: Save processed audio to GCS
            temp_file_path = f"temp_audio_{os.urandom(8).hex()}.wav"
            with open(temp_file_path, "wb") as f:
                f.write(audio_file)

            # Upload to GCS with unique identifier
            gcs_path = f"audio-files-and-transcripts/{os.path.basename(temp_file_path)}"
            self.upload_to_gcs(temp_file_path, gcs_path)

            # Clean up local file
            os.remove(temp_file_path)

            # Return combined results
            return self.combine_results(transcriptions)
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise
            
    def combine_results(self, transcriptions):
        """Combine chunk transcriptions into final result."""
        combined_text = ""
        for i, trans in enumerate(transcriptions):
            # Remove overlap duplicates
            if i > 0:
                # Simple overlap removal (can be improved)
                words = trans.split()
                prev_words = transcriptions[i-1].split()
                overlap_size = min(len(words), len(prev_words)) // 4
                trans = " ".join(words[overlap_size:])
            
            combined_text += trans + " "
            
        return combined_text.strip()
    
    def transcribe_batch_files(self, audio_files):
        """Process multiple audio files in parallel."""
        futures = []
        results = {}
        
        # Submit tasks
        for audio_file in audio_files:
            future = self.executor.submit(self.transcribe_file, audio_file)
            futures.append((audio_file, future))
        
        # Collect results
        for audio_file, future in futures:
            try:
                result = future.result()
                results[audio_file] = {
                    "status": "success",
                    "transcription": result
                }
            except Exception as e:
                results[audio_file] = {
                    "status": "error",
                    "error": str(e)
                }
                
        return results

    def sanitize_filename(self, title):
        """Sanitize the filename by removing invalid characters."""
        # Remove invalid characters and replace spaces with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Limit length and remove trailing spaces/underscores
        sanitized = sanitized[:100].strip('_').strip()
        return sanitized

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
    def upload_audio_from_youtube(self, youtube_url):
        """Download and process audio from a YouTube link with retries."""
        audio_path = None
        try:
            logger.info(f"Downloading audio from YouTube link: {youtube_url}")
        
            
            # Use AudioDownloader to get the file
            audio_path, video_title = self.downloader.download_youtube_video(youtube_url)
            
            if not os.path.exists(audio_path):
                raise Exception("Downloaded file not found")
                
            # Upload to GCS
            gcs_path = f"audio-files/{os.path.basename(audio_path)}"
            self.upload_to_gcs(audio_path, gcs_path)

            # Clean up any existing downloads with same name pattern
            for file in os.listdir(self.downloader.output_dir):
                if file.endswith('.mp3') or file.endswith('.mp4'):
                    try:
                        os.remove(os.path.join(self.downloader.output_dir, file))
                    except Exception:
                        pass
            
        except Exception as e:
            logger.error(f"Error processing YouTube link {youtube_url}: {str(e)}")
            # Ensure cleanup on error
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass
            # Reset the downloader's progress bar
            if hasattr(self.downloader, 'pbar') and self.downloader.pbar:
                self.downloader.pbar.close()
                self.downloader.pbar = None
            raise

# Initialize the pipeline (replace with actual preprocessor and inference client)
pipeline = AudioPipeline(preprocessor=None, inference_client=None, gcs_bucket_name="audio-files-and-transcripts")

@app.post("/process-file/")
async def transcribe_file_endpoint(file: UploadFile):
    """API endpoint to process a single audio file."""
    try:
        logger.info(f"Received file: {file.filename}")
        audio_data = await file.read()
        result = pipeline.transcribe_file(audio_data)
        return {"status": "success", "transcription": result}
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/process-batch/")
async def transcribe_batch_endpoint(files: List[UploadFile]):
    """API endpoint to transcribe multiple audio files."""
    try:
        logger.info(f"Received {len(files)} files for batch transcribeing")
        audio_files = {file.filename: await file.read() for file in files}
        results = pipeline.transcribe_batch_files(audio_files)
        return results
    except Exception as e:
        logger.error(f"Error transcribeing batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error transcribeing batch: {str(e)}")

@app.post("/process-youtube/")
async def process_youtube_endpoint(youtube_url: str = Form(...)):
    """API endpoint to process audio from a YouTube link."""
    try:
        logger.info(f"Received YouTube link: {youtube_url}")
        result = pipeline.upload_audio_from_youtube(youtube_url)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing YouTube link: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing YouTube link: {str(e)}")


