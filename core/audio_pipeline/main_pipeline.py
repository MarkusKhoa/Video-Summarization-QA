from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from fastapi import FastAPI, UploadFile, HTTPException, Form
from typing import List
from pytube import YouTube
from tenacity import retry, stop_after_attempt, wait_fixed
from google.cloud import storage

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

    def process_file(self, audio_file):
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
            
            # Step 4: Save processed audio locally (temporary)
            temp_file_path = "temp_audio_file.wav"
            with open(temp_file_path, "wb") as f:
                f.write(audio_file)

            # Step 5: Upload to GCS
            gcs_path = f"processed_audio/{os.path.basename(temp_file_path)}"
            self.upload_to_gcs(temp_file_path, gcs_path)

            # Step 6: Clean up local file
            os.remove(temp_file_path)

            # Step 7: Combine results
            return self.combine_results(transcriptions)
        except Exception as e:
            logger.error(f"Error processing file {audio_file}: {str(e)}")
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
    
    def process_batch_files(self, audio_files):
        """Process multiple audio files in parallel."""
        futures = []
        results = {}
        
        # Submit tasks
        for audio_file in audio_files:
            future = self.executor.submit(self.process_file, audio_file)
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

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def process_youtube_link(self, youtube_url):
        """Download and process audio from a YouTube link with retries."""
        try:
            logger.info(f"Downloading audio from YouTube link: {youtube_url}")
            yt = YouTube(youtube_url)
            audio_stream = yt.streams.filter(only_audio=True).first()
            if not audio_stream:
                raise ValueError("No audio stream found for the given YouTube link.")
            
            # Download audio to memory
            audio_data = io.BytesIO()
            audio_stream.stream_to_buffer(audio_data)
            audio_data.seek(0)  # Reset buffer pointer
            
            # Save downloaded audio locally (temporary)
            temp_file_path = "temp_youtube_audio.mp3"
            with open(temp_file_path, "wb") as f:
                f.write(audio_data.getvalue())

            # Upload to GCS
            gcs_path = f"youtube_audio/{os.path.basename(temp_file_path)}"
            self.upload_to_gcs(temp_file_path, gcs_path)

            # Clean up local file
            os.remove(temp_file_path)

            # Process the audio
            return self.process_file(audio_data)
        except Exception as e:
            logger.error(f"Error processing YouTube link {youtube_url}: {str(e)}")
            raise

# Initialize the pipeline (replace with actual preprocessor and inference client)
pipeline = AudioPipeline(preprocessor=None, inference_client=None, gcs_bucket_name="your-gcs-bucket-name")

@app.post("/process-file/")
async def process_file_endpoint(file: UploadFile):
    """API endpoint to process a single audio file."""
    try:
        logger.info(f"Received file: {file.filename}")
        audio_data = await file.read()
        result = pipeline.process_file(audio_data)
        return {"status": "success", "transcription": result}
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/process-batch/")
async def process_batch_endpoint(files: List[UploadFile]):
    """API endpoint to process multiple audio files."""
    try:
        logger.info(f"Received {len(files)} files for batch processing")
        audio_files = {file.filename: await file.read() for file in files}
        results = pipeline.process_batch_files(audio_files)
        return results
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing batch: {str(e)}")

@app.post("/process-youtube/")
async def process_youtube_endpoint(youtube_url: str = Form(...)):
    """API endpoint to process audio from a YouTube link."""
    try:
        logger.info(f"Received YouTube link: {youtube_url}")
        result = pipeline.process_youtube_link(youtube_url)
        return {"status": "success", "transcription": result}
    except Exception as e:
        logger.error(f"Error processing YouTube link: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing YouTube link: {str(e)}")


