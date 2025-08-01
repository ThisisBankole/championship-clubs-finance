"""
Azure Blob Storage manager for PDF documents
"""

import structlog
from typing import Optional
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import AzureError
import os

logger = structlog.get_logger()


class BlobStorageManager:
    """Manages PDF document uploads to Azure Blob Storage"""
    
    def __init__(self):
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'financial-docs-container')
        
    async def upload_pdf(self, blob_path: str, pdf_content: bytes) -> bool:
        """Upload PDF content to blob storage"""
        
        try:
            async with BlobServiceClient.from_connection_string(
                self.connection_string
            ) as blob_service:
                
                blob_client = blob_service.get_blob_client(
                    container=self.container_name,
                    blob=blob_path
                )
                
                # Upload with overwrite
                await blob_client.upload_blob(
                    pdf_content,
                    overwrite=True,
                    content_type='application/pdf'
                )
                
                logger.info("PDF uploaded successfully",
                           blob_path=blob_path,
                           size_kb=len(pdf_content) // 1024)
                
                return True
                
        except AzureError as e:
            logger.error("Azure blob upload failed",
                        blob_path=blob_path,
                        error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error during upload",
                        blob_path=blob_path,
                        error=str(e))
            return False
    
    async def check_blob_exists(self, blob_path: str) -> bool:
        """Check if a blob already exists"""
        
        try:
            async with BlobServiceClient.from_connection_string(
                self.connection_string
            ) as blob_service:
                
                blob_client = blob_service.get_blob_client(
                    container=self.container_name,
                    blob=blob_path
                )
                
                return await blob_client.exists()
                
        except Exception as e:
            logger.error("Error checking blob existence",
                        blob_path=blob_path,
                        error=str(e))
            return False