import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from utils import get_batch_variation
from gemini_service import build_gemini_payload, generate_and_upload_image

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        config = request.json
        if not config:
            return jsonify({"status": "error", "message": "No configuration provided"}), 400
            
        print(f"[Handler] Received request to generate {config.get('output', {}).get('count', 1)} image(s).")
        
        # Extract Image Mapping (ATTACHED IMAGE N -> URL)
        image_mapping = {}
        sections_to_check = ["model", "outfits", "accessories", "environment"]
        
        for section in sections_to_check:
            items = config.get(section, [])
            if not isinstance(items, list):
                continue
            for item in items:
                # Handle single reference image or multiple
                refs = item.get('reference_images') or [item.get('reference_image')]
                urls = item.get('reference_image_urls') or []
                
                # Filter out None/empty values
                refs = [r for r in refs if r]
                
                for i, ref in enumerate(refs):
                    if i < len(urls) and urls[i]:
                        image_mapping[ref] = urls[i]
                        
        print(f"[Handler] Extracted {len(image_mapping)} reference image(s).")
        
        # Clean config (remove URLs for Gemini instruction text to save tokens/privacy)
        config_clean = json.loads(json.dumps(config))
        for section in sections_to_check:
            items = config_clean.get(section, [])
            if not isinstance(items, list):
                continue
            for item in items:
                item.pop('reference_image_urls', None)
                item.pop('reference_image_url', None)
                
        results = []
        count = config.get('output', {}).get('count', 1)
        variety = config.get('output', {}).get('batch_variety', 'subtle_variations')
        
        for i in range(count):
            print(f"[Handler] Processing image {i + 1}/{count}...")
            variation = get_batch_variation(variety, i) if count > 1 else ""
            
            payload = build_gemini_payload(config_clean, image_mapping, variation)
            image_url = generate_and_upload_image(payload)
            
            results.append(image_url)
            print(f"[Handler] Image {i + 1}/{count} generated and uploaded: {image_url}")
            
        print(f"[Handler] Generation process complete. Total images: {len(results)}")
        return jsonify({
            "status": "success",
            "message": f"Generated {len(results)} images",
            "data": {"images": results}
        }), 200
        
    except Exception as e:
        print(f"[Error] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
