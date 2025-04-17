from tritonclient.utils import np_to_triton_dtype
from loguru import logger

import tritonclient.grpc as grpcclient
import numpy as np
import time

class TritonInference:
    def __init__(self, url, model_name = "'whisper"):
        self.client = grpcclient.InferenceServerClient(url = url)
        self.model_name = model_name

    def prepare_input(self, audio_chunk):
        input_tensor = grpcclient.InferInput(
            "audio_input",
            audio_chunk.shape,
            np_to_triton_dtype(np.float32)
        )
    
    def process_batch(self, audio_chunks, batch_size=4):
        """Process a batch of audio chunks."""
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
        return results
