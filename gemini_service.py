import os
import json
import requests
import base64
import uuid
import time
from dotenv import load_dotenv
from utils import fetch_image_as_base64, upload_to_s3

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

def build_gemini_payload(config, image_mapping, variation=""):
    """Build the JSON payload for the Gemini API"""
    print(f"[build_gemini_payload] Building payload with variation: \"{variation}\"")
    
    instruction = f"Generate a photoshoot image based on this configuration:\n\n{json.dumps(config, indent=2)}\n\n{variation}\n\nFollow all rules specified in the configuration exactly."
    
    parts = [{"text": instruction}]
    
    # Sort image mapping keys numerically based on suffix (ATTACHED IMAGE 1, 2, ...)
    sorted_refs = sorted(image_mapping.keys(), key=lambda x: int(x.split(' ')[-1]))
    
    for ref in sorted_refs:
        url = image_mapping[ref]
        base64_data = fetch_image_as_base64(url)
        parts.append({
            "inlineData": {
                "mime_type": "image/jpeg",
                "data": base64_data
            }
        })
        
    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": config.get('output', {}).get('aspect_ratio', '2:3'),
                "imageSize": config.get('output', {}).get('quality', '4K')
            }
        }
    }

def generate_and_upload_image(payload):
    """Call Gemini API and upload resulting image to S3"""
    print(f"[generate_and_upload_image] Sending request to Gemini API...")
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    response = requests.post(GEMINI_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"[generate_and_upload_image] Gemini API error: {response.text}")
        raise Exception(f"Gemini API error: {response.text}")
    
    result = response.json()
    candidates = result.get('candidates', [])
    if not candidates:
        print(f"[generate_and_upload_image] No candidates in Gemini response: {json.dumps(result)}")
        raise Exception("No candidates in Gemini response")
        
    content_parts = candidates[0].get('content', {}).get('parts', [])
    image_part = next((p for p in content_parts if 'inlineData' in p), None)
    
    if not image_part:
        print(f"[generate_and_upload_image] No image data found in Gemini response: {json.dumps(result)}")
        raise Exception("No image data in Gemini response")
        
    print(f"[generate_and_upload_image] Successfully received image from Gemini.")
    
    base64_data = image_part['inlineData']['data']
    mime_type = image_part['inlineData'].get('mime_type', 'image/png')
    
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

def generate_quick_update(prompt, image_urls=None, aspect_ratio="2:3", resolution="4K"):
    """
    Simplified Quick Update generation: Prompt + optional reference images.
    """
    print(f"[generate_quick_update] Generating with prompt: {prompt[:50]}...")
    
    parts = [{"text": prompt}]
    
    if image_urls:
        for i, url in enumerate(image_urls[:14]): # Limit to 14 images as per Gemini best practices
            base64_data = fetch_image_as_base64(url)
            # Add explicit label so Gemini can reference it (e.g. "ATTACHED IMAGE 1")
            parts.append({"text": f"ATTACHED IMAGE {i+1}:"})
            parts.append({
                "inlineData": {
                    "mime_type": "image/jpeg",
                    "data": base64_data
                }
            })

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": resolution
            }
        }
    }

    return generate_and_upload_image(payload)
