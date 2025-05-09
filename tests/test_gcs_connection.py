import os
import pytest
from google.cloud import storage
from loguru import logger

class TestGCSConnection:
    def __init__(self):
        self.bucket_name = "audio-files-and-transcripts"  # Replace with your bucket name
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {str(e)}")
            raise

    def test_bucket_exists(self):
        """Test if the bucket exists and is accessible."""
        try:
            assert self.bucket.exists(), f"Bucket {self.bucket_name} does not exist"
            logger.info(f"Successfully connected to bucket: {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to access bucket: {str(e)}")
            return False

    def test_upload_download(self):
        """Test upload and download operations."""
        test_content = b"Test content for GCS connection"
        test_blob_name = "/home/khoa/Workspace/multimodal-RAG/data/Kỳ Án Nữ Tiếp Viên Trong Tủ Quần Áo - Khi Gato Biến Thành Ác Quỷ - Tra Án.mp3"
        
        try:
            # Test upload
            blob = self.bucket.blob(test_blob_name)
            blob.upload_from_string(test_content)
            logger.info(f"Successfully uploaded test file: {test_blob_name}")

            # Test download
            downloaded_content = blob.download_as_bytes()
            assert downloaded_content == test_content
            logger.info("Successfully downloaded and verified test file")

            # Cleanup
            blob.delete()
            logger.info("Successfully cleaned up test file")
            
            return True
        except Exception as e:
            logger.error(f"Failed upload/download test: {str(e)}")
            return False

def main():
    """
    Before running this test:
    1. Create a service account in Google Cloud Console
    2. Download the JSON key file
    3. Set the environment variable to point to your key file:
       export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-key.json"
    """
    # Check if credentials are set
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        logger.info("Please set it to the path of your service account key JSON file")
        return
    
    if not os.path.exists(creds_path):
        logger.error(f"❌ Credentials file not found at: {creds_path}")
        return

    logger.info(f"Using credentials from: {creds_path}")
    
    # Run tests
    gcs_test = TestGCSConnection()
    
    # Test bucket connection
    if gcs_test.test_bucket_exists():
        logger.info("✅ GCS bucket connection test passed")
    else:
        logger.error("❌ GCS bucket connection test failed")

    # Test upload/download
    if gcs_test.test_upload_download():
        logger.info("✅ GCS upload/download test passed")
    else:
        logger.error("❌ GCS upload/download test failed")

if __name__ == "__main__":
    main()
