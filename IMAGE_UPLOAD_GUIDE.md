# Image Upload & Analysis Guide

## Overview

The RAPP system now includes a robust two-step image upload and analysis system:

1. **UploadImage Agent**: Uploads images to Azure File Storage and generates secure access URLs
2. **AnalyzeImage Agent**: Analyzes images using Azure OpenAI Vision API

## How It Works

### Step 1: Image Upload

When you attach an image (via file picker, drag-and-drop, or paste):

1. The frontend displays a preview of the image
2. The image is automatically uploaded to Azure File Storage via the `UploadImage` agent
3. A secure SAS URL is generated (valid for 24 hours)
4. The URL is stored and ready for analysis

### Step 2: Image Analysis

When you send your message with the attached image:

1. The secure Azure Storage URL is passed to the `AnalyzeImage` agent
2. The image is analyzed using Azure OpenAI's Vision API (GPT-4 Vision)
3. A detailed description is returned

## User Experience

### Uploading an Image

1. **Click the upload button** or **drag & drop** an image into the chat
2. You'll see a preview with an upload status indicator
3. Status messages:
   - 🔄 "Uploading image to storage..." - Upload in progress
   - ✅ "Image uploaded successfully!" - Ready for analysis
   - ❌ "Upload failed: [error]" - Something went wrong (falls back to base64)

### Analyzing an Image

Once uploaded, simply type your question or request:
- "What's in this image?"
- "Describe this photo"
- "Analyze this image"

The system will automatically use the uploaded image URL for analysis.

## Technical Details

### Agents

#### UploadImageAgent
- **Location**: `agents/upload_image_agent.py`
- **Function**: Uploads images to Azure File Storage
- **Returns**: Secure SAS URL valid for 24 hours
- **Storage Location**: `uploaded_images/` directory in Azure File Share

#### AnalyzeImageAgent
- **Location**: `agents/analyze_image_agent.py`
- **Function**: Analyzes images using Vision AI
- **Supports**:
  - Azure File Storage URLs (with SAS tokens)
  - Regular HTTP/HTTPS URLs
  - Base64 encoded images (data URLs)
  - Raw base64 strings

### API Integration

#### Upload Flow

```javascript
POST /api/businessinsightbot_function
{
  "user_input": "Please upload this image: filename.jpg",
  "conversation_history": [],
  "user_guid": "user-guid",
  "image_data": "data:image/jpeg;base64,..."
}
```

Response contains the Azure Storage URL:
```
Image uploaded successfully!
Filename: uploaded_image_20250124_143022.jpg
URL: https://account.file.core.windows.net/share/uploaded_images/filename.jpg?sas_token
```

#### Analysis Flow

```javascript
POST /api/businessinsightbot_function
{
  "user_input": "Analyze this image",
  "conversation_history": [
    {
      "role": "user",
      "content": "https://account.file.core.windows.net/share/uploaded_images/filename.jpg?sas_token"
    }
  ],
  "user_guid": "user-guid"
}
```

## Configuration

### Required Environment Variables

```bash
# Azure Storage (for image upload)
AzureWebJobsStorage="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=..."
AZURE_FILES_SHARE_NAME="your-share-name"

# Azure OpenAI (for image analysis)
AZURE_OPENAI_API_KEY="your-api-key"
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
AZURE_OPENAI_API_VERSION="2024-02-01"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"  # Must support vision
```

### Azure OpenAI Model Requirements

The analyze agent requires a vision-capable model:
- **Recommended**: `gpt-4o`, `gpt-4-vision`, `gpt-4-turbo`
- **Not Compatible**: `gpt-3.5-turbo`, `gpt-4` (non-vision)

## Error Handling

### Upload Errors

If upload fails:
1. Error message is displayed in the UI
2. System falls back to base64 encoding
3. Image can still be analyzed (but may be slower/larger payload)

### Analysis Errors

Common issues:
- **Invalid base64**: Check image encoding
- **Missing environment variables**: Configure Azure OpenAI settings
- **Model not found**: Ensure deployment name is correct
- **Timeout**: Large images may take longer to analyze

## Best Practices

1. **Use supported formats**: JPEG, PNG, GIF, BMP
2. **Optimal size**: Under 4MB for best performance
3. **Clear images**: Higher quality = better analysis
4. **Specific prompts**: Ask specific questions for better results

## Advanced Usage

### Custom Analysis Prompts

You can provide custom prompts to the AnalyzeImage agent:

```python
{
  "image_source": "https://...",
  "prompt": "Identify all text visible in this image and transcribe it"
}
```

### Programmatic Access

```python
# Upload an image
upload_agent = UploadImageAgent()
result = upload_agent.perform(
    image_data="data:image/jpeg;base64,...",
    filename="my_image.jpg"
)

# Analyze the uploaded image
analyze_agent = AnalyzeImageAgent()
result = analyze_agent.perform(
    image_source="https://account.file.core.windows.net/...",
    prompt="What objects are visible in this image?"
)
```

## Troubleshooting

### Image Won't Upload

1. Check Azure Storage connection string
2. Verify file share name is correct
3. Check file share permissions
4. Ensure storage account is accessible

### Analysis Fails

1. Verify Azure OpenAI endpoint is configured
2. Check API key is valid
3. Ensure deployment supports vision (gpt-4o/gpt-4-vision)
4. Check Azure OpenAI quota/limits

### SAS Token Expired

- Tokens are valid for 24 hours
- Re-upload the image to generate a new token
- For longer retention, adjust `expiry` parameter in `_generate_sas_url()`

## Security Considerations

1. **SAS Tokens**: Limited to 24-hour validity
2. **Storage**: Images stored in private Azure File Share
3. **Access**: Only accessible via SAS token
4. **Cleanup**: Consider implementing automated cleanup for old images

## Future Enhancements

- [ ] Image compression before upload
- [ ] Thumbnail generation
- [ ] Multiple image analysis
- [ ] OCR extraction
- [ ] Object detection
- [ ] Image comparison
- [ ] Automated image cleanup
