import os
import requests
import base64
import json
import logging
from agents.basic_agent import BasicAgent
from openai import AzureOpenAI

class AnalyzeImageAgent(BasicAgent):
    def __init__(self):
        self.name = "AnalyzeImage"
        self.metadata = {
            "name": self.name,
            "description": "Analyzes an image using Azure OpenAI's multimodal capabilities (gpt-5-chat). Can accept an image URL (including Azure File Storage URLs), or a Base64 encoded image string. For best results, upload the image first using UploadImage agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_source": {
                        "type": "string",
                        "description": "URL of the image to be analyzed (including Azure File Storage URLs with SAS tokens), or a Base64 encoded image string."
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Optional custom prompt for analyzing the image. If not provided, a general analysis will be performed.",
                        "default": "Analyze this image and provide a detailed description."
                    }
                },
                "required": ["image_source"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        """
        Analyze an image using Vision AI.

        Args:
            image_source (str): URL of the image to be analyzed, or a Base64 encoded image string.
            prompt (str, optional): Custom prompt for analysis

        Returns:
            str: A detailed description of the image content.
        """
        try:
            image_source = kwargs.get('image_source')
            custom_prompt = kwargs.get('prompt', "Analyze this image and provide a detailed description.")

            if not image_source:
                return "Error: No image source provided."

            # Determine the data URL format to use
            data_url = None

            # Handle image URLs (including Azure File Storage URLs with SAS)
            if image_source.startswith(('http://', 'https://')):
                # Check if it's an Azure File Storage URL
                if 'file.core.windows.net' in image_source:
                    logging.info("Detected Azure File Storage URL with SAS token")
                    # For Azure File Storage URLs with SAS, we'll download and convert to base64
                    try:
                        encoded_image = self._encode_image_from_url(image_source)
                        # Determine format from URL if possible
                        if '.png' in image_source.lower():
                            data_url = f"data:image/png;base64,{encoded_image}"
                        elif '.jpg' in image_source.lower() or '.jpeg' in image_source.lower():
                            data_url = f"data:image/jpeg;base64,{encoded_image}"
                        else:
                            data_url = f"data:image/png;base64,{encoded_image}"
                    except Exception as e:
                        logging.error(f"Error processing Azure File Storage URL: {str(e)}")
                        return f"Failed to process Azure File Storage URL: {str(e)}"
                else:
                    # Regular HTTP/HTTPS URLs
                    try:
                        encoded_image = self._encode_image_from_url(image_source)
                        data_url = f"data:image/jpeg;base64,{encoded_image}"
                    except Exception as e:
                        logging.error(f"Error processing image URL: {str(e)}")
                        return f"Failed to process image URL: {str(e)}"

            # Handle data URLs (keeping original format)
            elif image_source.startswith('data:image'):
                # Extract the base64 part from the data URL
                try:
                    parts = image_source.split(',', 1)
                    if len(parts) != 2:
                        return "Error: Invalid data URL format"

                    # Get the base64 content and fix padding issues
                    base64_content = parts[1]
                    # Fix padding if needed (length must be a multiple of 4)
                    mod = len(base64_content) % 4
                    if mod > 0:
                        base64_content += '=' * (4 - mod)

                    try:
                        # Validate the corrected base64 content
                        base64.b64decode(base64_content, validate=True)
                        # Reconstruct the data URL with fixed padding
                        data_url = f"{parts[0]},{base64_content}"
                    except Exception as e:
                        logging.error(f"Invalid base64 data in data URL: {str(e)}")
                        return f"Invalid base64 data in data URL: {str(e)}"
                except Exception as e:
                    logging.error(f"Error processing data URL: {str(e)}")
                    return f"Error processing data URL: {str(e)}"

            # Handle raw base64 strings
            else:
                try:
                    # Fix padding issues for raw base64 strings
                    mod = len(image_source) % 4
                    if mod > 0:
                        image_source += '=' * (4 - mod)

                    try:
                        # Verify the base64 string is valid
                        base64.b64decode(image_source, validate=True)
                        # Assume PNG if no format specified
                        data_url = f"data:image/png;base64,{image_source}"
                    except Exception as e:
                        logging.error(f"Invalid base64 string: {str(e)}")
                        return f"Invalid base64 string: {str(e)}"
                except Exception as e:
                    logging.error(f"Error processing base64 data: {str(e)}")
                    return f"Error processing base64 data: {str(e)}"

            if not data_url:
                return "Error: Could not process the image data provided."

            # Log the data URL format (without the actual data for security)
            format_part = data_url.split(',')[0] if ',' in data_url else data_url[:30]
            logging.info(f"Using image format: {format_part}")

            # Initialize the Azure OpenAI client
            client = self._get_openai_client()

            # Create the messages payload for the API request
            messages = [
                {
                    "role": "system",
                    "content": "You are an AI assistant that analyzes images and provides detailed, accurate descriptions."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        },
                        {
                            "type": "text",
                            "text": custom_prompt
                        }
                    ]
                }
            ]

            # Request analysis from the model
            # Use the standard deployment - gpt-5-chat is multimodal
            response = client.chat.completions.create(
                model=os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-5-chat'),
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )

            return response.choices[0].message.content

        except Exception as e:
            logging.error(f"Error in AnalyzeImageAgent: {str(e)}")
            return f"An error occurred while analyzing the image: {str(e)}"

    def _encode_image_from_url(self, image_url):
        """Encode an image from a URL to base64."""
        try:
            # Add timeout and proper headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
        except requests.RequestException as e:
            logging.error(f"Error fetching image from URL: {str(e)}")
            raise Exception(f"Failed to fetch image from URL: {str(e)}")

    def _get_openai_client(self):
        """Initialize and return an AzureOpenAI client."""
        try:
            client = AzureOpenAI(
                api_key=os.environ['AZURE_OPENAI_API_KEY'],
                api_version=os.environ['AZURE_OPENAI_API_VERSION'],
                azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
            )
            return client
        except KeyError as e:
            logging.error(f"Missing environment variable: {str(e)}")
            raise Exception(f"Missing required environment variable: {str(e)}")
        except Exception as e:
            logging.error(f"Error initializing AzureOpenAI client: {str(e)}")
            raise Exception(f"Failed to initialize AzureOpenAI client: {str(e)}")
