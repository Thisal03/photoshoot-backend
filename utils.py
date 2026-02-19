import os
import boto3
import base64
import requests
import uuid
from botocore.config import Config
from dotenv import load_dotenv
from config import SECTIONS, BATCH_VARIATIONS

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'eu-north-1')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'crowai-image-bucket')
CLOUDFRONT_DOMAIN = os.getenv('CLOUDFRONT_DOMAIN')

# S3 Client Configuration
s3_config = Config(
    region_name=AWS_REGION,
    signature_version='s3v4',
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    config=s3_config
)

def get_public_url(key):
    """Get public URL for an S3 object (CloudFront or direct S3)"""
    clean_key = key.lstrip('/')
    if CLOUDFRONT_DOMAIN:
        return f"https://{CLOUDFRONT_DOMAIN}/{clean_key}"
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{clean_key}"

def get_category_folder(image_type):
    """Map image types to folder categories based on the standard structure"""
    folder_map = {
        "model_ref": "model-refs",
        "outfit": "outfit-refs",
        "jewelry": "jewelry-refs",
        "environment": "environment-refs",
        "pose": "pose-refs",
        "hair": "hair-refs",
        "quick_update": "quick-update-refs"
    }
    return folder_map.get(image_type, "other-refs")

def upload_to_s3(key, data, content_type):
    """Upload file to S3 and return public URL"""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl='max-age=3600'
        )
        return {
            'success': True,
            'public_url': get_public_url(key)
        }
    except Exception as e:
        print(f"S3 upload error for {key}: {str(e)}")
        return {
            'success': False,
            'public_url': '',
            'error': str(e)
        }

def fetch_image_as_base64(image_url):
    """Fetch image from URL and convert to base64"""
    print(f"[fetch_image_as_base64] Fetching image from URL: {image_url[:100]}...")
    response = requests.get(image_url)
    if response.status_code != 200:
        print(f"[fetch_image_as_base64] Failed to fetch image: {response.status_code}")
        raise Exception(f"Failed to fetch image: {response.status_code}")
    
    return base64.b64encode(response.content).decode('utf-8')

def get_rules_for_item(section_key, item_type, item_text="", strength=0.8, image_indices=None):
    """Format prompt rules based on item configuration"""
    if image_indices is None:
        image_indices = []
        
    section = SECTIONS.get(section_key, {})
    rules_dict = section.get('rules', {})
    rules_template = rules_dict.get(item_type) or rules_dict.get('default') or []

    formatted_rules = []
    for rule in rules_template:
        formatted = rule.replace("{type}", item_type) \
                        .replace("{text}", item_text) \
                        .replace("{strength}", str(int(strength * 100)))
        
        for i, idx in enumerate(image_indices):
            formatted = formatted.replace(f"{{img_{i + 1}_idx}}", str(idx))
            
        formatted_rules.append(formatted)
        
    return formatted_rules

def get_batch_variation(variety, index):
    """Get variation string for batch generation"""
    variations = BATCH_VARIATIONS.get(variety) or BATCH_VARIATIONS.get('subtle_variations')
    return variations[index % len(variations)]
