import os
import base64
import logging
from datetime import datetime, timedelta
from agents.basic_agent import BasicAgent
from utils.azure_file_storage import AzureFileStorageManager
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

class UploadImageAgent(BasicAgent):
    def __init__(self):
        self.name = "UploadImage"
        self.metadata = {
            "name": self.name,
            "description": "Uploads an image to Azure File Storage and returns a secure URL that can be used for analysis. Accepts base64 encoded image data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_data": {
                        "type": "string",
                        "description": "Base64 encoded image data (with or without data URL prefix)"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional filename for the image. If not provided, a timestamp-based name will be generated."
                    }
                },
                "required": ["image_data"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)
        self.storage_manager = AzureFileStorageManager()

    def _extract_base64_from_data_url(self, data_url):
        """Extract base64 content from a data URL."""
        if data_url.startswith('data:'):
            parts = data_url.split(',', 1)
            if len(parts) == 2:
                return parts[1]
        return data_url

    def _fix_base64_padding(self, base64_string):
        """Fix base64 padding if needed."""
        mod = len(base64_string) % 4
        if mod > 0:
            base64_string += '=' * (4 - mod)
        return base64_string

    def _generate_sas_url(self, file_path):
        """Generate a SAS URL for the uploaded image."""
        try:
            storage_connection = os.environ.get('AzureWebJobsStorage', '')
            if not storage_connection:
                raise ValueError("AzureWebJobsStorage connection string is required")

            # Parse connection string
            connection_parts = dict(part.split('=', 1) for part in storage_connection.split(';'))
            account_name = connection_parts.get('AccountName')
            account_key = connection_parts.get('AccountKey')

            if not all([account_name, account_key]):
                raise ValueError("Invalid storage connection string")

            # Generate SAS token with read permissions valid for 24 hours
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.storage_manager.share_name,
                blob_name=file_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=24)
            )

            # Construct the full URL
            sas_url = f"https://{account_name}.file.core.windows.net/{self.storage_manager.share_name}/{file_path}?{sas_token}"
            return sas_url

        except Exception as e:
            logging.error(f"Error generating SAS URL: {str(e)}")
            # Return a fallback URL without SAS
            return f"https://{account_name}.file.core.windows.net/{self.storage_manager.share_name}/{file_path}"

    def perform(self, **kwargs):
        """
        Upload an image to Azure File Storage and return a secure URL.

        Args:
            image_data (str): Base64 encoded image data
            filename (str, optional): Desired filename for the image

        Returns:
            str: A message with the uploaded image URL
        """
        try:
            image_data = kwargs.get('image_data')
            filename = kwargs.get('filename')

            if not image_data:
                return "Error: No image data provided."

            # Extract base64 content if it's a data URL
            base64_content = self._extract_base64_from_data_url(image_data)

            # Fix padding if needed
            base64_content = self._fix_base64_padding(base64_content)

            # Decode base64 to bytes
            try:
                image_bytes = base64.b64decode(base64_content, validate=True)
            except Exception as e:
                logging.error(f"Failed to decode base64 image: {str(e)}")
                return f"Error: Invalid base64 image data - {str(e)}"

            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Try to detect image format from data URL or default to png
                if image_data.startswith('data:image/'):
                    format_part = image_data.split(';')[0].split('/')[-1]
                    filename = f"uploaded_image_{timestamp}.{format_part}"
                else:
                    filename = f"uploaded_image_{timestamp}.png"

            # Ensure directory exists and upload the image
            directory = 'uploaded_images'
            self.storage_manager.ensure_directory_exists(directory)

            success = self.storage_manager.write_file(directory, filename, image_bytes)

            if not success:
                return "Error: Failed to upload image to Azure File Storage"

            # Generate accessible URL
            file_path = f"{directory}/{filename}"
            image_url = self._generate_sas_url(file_path)

            logging.info(f"Successfully uploaded image: {filename}")

            return f"Image uploaded successfully!\nFilename: {filename}\nURL: {image_url}\n\nYou can now analyze this image using the AnalyzeImage agent."

        except Exception as e:
            logging.error(f"Error in UploadImageAgent: {str(e)}")
            return f"An error occurred while uploading the image: {str(e)}"
