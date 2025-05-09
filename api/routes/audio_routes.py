from fastapi import APIRouter, UploadFile, HTTPException, Form
from typing import List
from loguru import logger
from core.audio_pipeline.main_pipeline import AudioPipeline

router = APIRouter()

# Initialize the pipeline (replace with actual preprocessor and inference client)
pipeline = AudioPipeline(
    preprocessor=None, 
    inference_client=None, 
    gcs_bucket_name="audio-files-and-transcripts"
)

@router.post("/process-file/")
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

@router.post("/process-batch/")
async def transcribe_batch_endpoint(files: List[UploadFile]):
    """API endpoint to transcribe multiple audio files."""
    try:
        logger.info(f"Received {len(files)} files for batch processing")
        audio_files = {file.filename: await file.read() for file in files}
        results = pipeline.transcribe_batch_files(audio_files)
        return results
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing batch: {str(e)}")

@router.post("/process-youtube/")
async def process_youtube_endpoint(youtube_url: str = Form(...)):
    """API endpoint to process audio from a YouTube link."""
    try:
        logger.info(f"Received YouTube link: {youtube_url}")
        result = pipeline.upload_audio_from_youtube(youtube_url)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing YouTube link: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing YouTube link: {str(e)}")

@router.post("/transcribe-gcs/")
async def transcribe_gcs_audio(bucket_name: str, blob_path: str):
    """Transcribe audio file directly from GCS."""
    try:
        logger.info(f"Processing audio from GCS: {bucket_name}/{blob_path}")
        transcript = pipeline.inference_client.transcribe_gcs_audio(
            bucket_name=bucket_name,
            blob_path=blob_path
        )
        return {
            "status": "success",
            "transcript": transcript,
            "source": f"gs://{bucket_name}/{blob_path}"
        }
    except Exception as e:
        logger.error(f"Error transcribing GCS audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error transcribing GCS audio: {str(e)}"
        )
