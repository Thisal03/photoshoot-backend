import os
import json
import requests
import base64
import uuid
import time
import tempfile
import ijson
from dotenv import load_dotenv
from utils import fetch_image_as_base64, upload_to_s3

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

def build_gemini_payload(config, image_mapping, variation=""):
    """Build the JSON payload for the Gemini API into a temporary file"""
    print(f"[build_gemini_payload] Building disk-buffered payload with variation: \"{variation}\"")
    
    tmp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json', encoding='utf-8')
    try:
        # Start JSON
        tmp.write('{"contents": [{"role": "user", "parts": [')
        
        # Part 1: Instruction
        instruction = f"Generate a photoshoot image based on this configuration:\n\n{json.dumps(config, indent=2)}\n\n{variation}\n\nFollow all rules specified in the configuration exactly."
        tmp.write(json.dumps({"text": instruction}))
        
        # Part 2: Images (processed one by one to save RAM)
        sorted_refs = sorted(image_mapping.keys(), key=lambda x: int(x.split(' ')[-1]))
        for ref in sorted_refs:
            tmp.write(",")
            url = image_mapping[ref]
            # Fetch and encode one image at a time
            base64_data = fetch_image_as_base64(url)
            tmp.write(json.dumps({
                "inlineData": {
                    "mime_type": "image/jpeg",
                    "data": base64_data
                }
            }))
            # Free memory explicitly if possible, though Python manages this
            del base64_data
            
        # End contents, start generationConfig
        tmp.write(']}], "generationConfig": {')
        tmp.write('"responseModalities": ["IMAGE"],')
        tmp.write('"imageConfig": {')
        tmp.write(f'"aspectRatio": {json.dumps(config.get("output", {}).get("aspect_ratio", "2:3"))},')
        tmp.write(f'"imageSize": {json.dumps(config.get("output", {}).get("quality", "4K"))}')
        tmp.write('}}}')
        
        tmp.flush()
        tmp_name = tmp.name
        tmp.close()
        return tmp_name
    except Exception as e:
        tmp.close()
        if os.path.exists(tmp.name):
            os.remove(tmp.name)
        raise e

def generate_and_upload_image(payload_path):
    """Call Gemini API using a disk-buffered payload and streaming response parsing"""
    print(f"[generate_and_upload_image] Sending streaming request to Gemini API...")
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    try:
        # Use a context manager for the file handle to ensure it's closed
        with open(payload_path, 'rb') as payload_file:
            # stream=True is critical for reading the response chunk-by-chunk
            response = requests.post(GEMINI_URL, headers=headers, data=payload_file, stream=True, timeout=300)
            
        # Clean up the payload file immediately after opening the request
        if os.path.exists(payload_path):
            os.remove(payload_path)
            
        if response.status_code != 200:
            error_text = response.text
            print(f"[generate_and_upload_image] Gemini API error: {error_text}")
            raise Exception(f"Gemini API error: {error_text}")
            
        print(f"[generate_and_upload_image] Response received. Starting incremental parsing...")
        
        # Use ijson.parse to extract both mimeType and data in one streaming pass
        parser = ijson.parse(response.raw)
        base64_data = None
        mime_type = "image/png" # Default fallback
        
        for prefix, event, value in parser:
            if prefix == 'candidates.item.content.parts.item.inlineData.data':
                base64_data = value
            elif prefix == 'candidates.item.content.parts.item.inlineData.mimeType':
                mime_type = value
        
        if not base64_data:
            raise Exception("No image data found in Gemini response")
            
        print(f"[generate_and_upload_image] Successfully extracted image data (length: {len(base64_data)}). Format: {mime_type}")
        
        # Convert base64 to binary
        image_bytes = base64.b64decode(base64_data)
        
        # Generate filename
        file_extension = mime_type.split('/')[-1] if '/' in mime_type else 'png'
        file_name = f"photoshoot_{int(time.time())}_{uuid.uuid4().hex[:8]}.{file_extension}"
        s3_key = f"generated-images/model-photoshoots/output/{file_name}"
        
        print(f"[generate_and_upload_image] Uploading to S3: {s3_key}")
        upload_result = upload_to_s3(s3_key, image_bytes, mime_type)
        
        if not upload_result['success']:
            raise Exception(f"S3 upload failed: {upload_result.get('error')}")
            
        return upload_result['public_url']
        
    except Exception as e:
        # Final cleanup for the payload file if something went wrong before removal
        if os.path.exists(payload_path):
            os.remove(payload_path)
        raise e

def generate_quick_update(prompt, image_urls=None, aspect_ratio="2:3", resolution="4K"):
    """
    Simplified Quick Update generation: Prompt + optional reference images with disk-buffering.
    """
    print(f"[generate_quick_update] Generating with prompt: {prompt[:50]}...")
    
    tmp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json', encoding='utf-8')
    try:
        # Start JSON
        tmp.write('{"contents": [{"role": "user", "parts": [')
        
        # Part 1: Prompt
        tmp.write(json.dumps({"text": prompt}))
        
        # Part 2: Images
        if image_urls:
            for i, url in enumerate(image_urls[:14]): # Limit to 14 images
                tmp.write(",")
                base64_data = fetch_image_as_base64(url)
                # Add explicit label
                tmp.write(json.dumps({"text": f"ATTACHED IMAGE {i+1}:"}))
                tmp.write(",")
                tmp.write(json.dumps({
                    "inlineData": {
                        "mime_type": "image/jpeg",
                        "data": base64_data
                    }
                }))
                del base64_data

        # End contents, start generationConfig
        tmp.write(']}], "generationConfig": {')
        tmp.write('"responseModalities": ["IMAGE"],')
        tmp.write('"imageConfig": {')
        tmp.write(f'"aspectRatio": {json.dumps(aspect_ratio)},')
        tmp.write(f'"imageSize": {json.dumps(resolution)}')
        tmp.write('}}}')
        
        tmp.flush()
        tmp_name = tmp.name
        tmp.close()
        return generate_and_upload_image(tmp_name)
        
    except Exception as e:
        tmp.close()
        if os.path.exists(tmp.name):
            os.remove(tmp.name)
        raise e
