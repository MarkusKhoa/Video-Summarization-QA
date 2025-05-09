from tritonclient.utils import np_to_triton_dtype
from loguru import logger
from prometheus_client import Summary, Counter
from .preprocessor import AudioPreprocessor

import tritonclient.grpc as grpcclient
import numpy as np
import time

class TritonInference:
    def __init__(self, url, model_name="whisper"):
        self.client = grpcclient.InferenceServerClient(url=url)
        self.model_name = model_name
        self.preprocessor = AudioPreprocessor()

        # Add metrics
        self.inference_duration = Summary(
            'inference_duration_seconds',
            'Time spent processing audio'
        )
        self.audio_processed = Counter(
            'audio_processing_total',
            'Number of audio files processed'
        )

    def prepare_input(self, audio_chunk):
        input_tensor = grpcclient.InferInput(
            "audio_input",
            audio_chunk.shape,
            np_to_triton_dtype(np.float32)
        )
    
    @self.inference_duration.time()
    def process_batch(self, audio_chunks, batch_size=4):
        """Process a batch of audio chunks with metrics."""
        try:
            results = []
            
            # Process in batches
            for i in range(0, len(audio_chunks), batch_size):
                batch = audio_chunks[i:i + batch_size]
                
                # Prepare batch input
                batch_input = np.stack(batch)
                input_tensor = self.prepare_input(batch_input)
                
                # Run inference
                response = self.client.infer(
                    self.model_name,
                    [input_tensor]
                )
                
                # Get results
                batch_results = response.as_numpy("transcription")
                results.extend(batch_results)
            
            logger.info(f"Processed {len(results)} chunks successfully.")
            self.audio_processed.inc(len(audio_chunks))
            return results
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            raise

    def transcribe_gcs_audio(self, bucket_name: str, blob_path: str):
        """Transcribe audio file from GCS."""
        try:
            # Load and preprocess audio
            audio_data = self.preprocessor.load_audio_from_gcs(bucket_name, blob_path)
            chunks = self.preprocessor.chunk_audio(audio_data)
            
            # Run inference on chunks
            results = self.process_batch(chunks)
            
            # Combine results
            transcript = " ".join(results)
            
            return transcript
            
        except Exception as e:
            logger.error(f"Error transcribing GCS audio: {str(e)}")
            raise
