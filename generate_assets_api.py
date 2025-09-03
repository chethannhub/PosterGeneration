import json
import mimetypes
import os
from flask import request, jsonify
from google.genai import types
from utils import load_scripts, save_scripts, IMAGES_DIR

MODEL = os.getenv("MODEL")
if not MODEL:
    raise RuntimeError("MODEL must be set in environment variables")

IMAGE_MODEL = os.getenv("IMAGE_MODEL")
if not IMAGE_MODEL:
    raise RuntimeError("IMAGE_MODEL must be set in environment variables")


def save_binary_file(file_name, data: bytes):
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"[DEBUG] File saved: {file_name}")


def generate_image_from_prompt(client, prompt: str, img_id: str):
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]  
        )
    )

    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            data_buffer = part.inline_data.data  # raw bytes
            file_extension = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
            img_path = os.path.join(IMAGES_DIR, f"{img_id}{file_extension}")
            save_binary_file(img_path, data_buffer)
            return img_path

    print(f"[WARNING] No image data returned for prompt: {prompt}")
    return None


def generate_assets(client):
    def handler():
        scripts = load_scripts()
        
        scripts = {str(k): v for k, v in scripts.items()}

        data = request.json
        script_id = str(data.get("id"))

        if script_id not in scripts:
            return jsonify({
                "error": "Invalid script ID",
                "requested_id": script_id,
                "available_ids": list(scripts.keys())
            }), 400
            

        script_info = scripts[script_id]

        prompt = f"""
You are a creative ad poster assistant.
Generate ONLY the assets section for this campaign.

Product: {script_info['product']}
Size: {script_info['size']}
Script: {script_info['script']}
Tagline: {script_info.get('tagline', '')}
example of 
Return JSON strictly in this format (no explanations, no markdown):

{{
  "styling": {{
    "background": {{
      "type": "color", 
      "value": "#RRGGBB"
    }},
    "fonts": {{
      "headline": {{ "color": "#000000", "align": "center" }},
      "body": {{ "color": "#333333", "align": "left" }},
      "cta": {{ "color": "#FFFFFF", "align": "center" }}
    }},
    "layout": {{
      "headline": {{ "x": 0.5, "y": 0.1 }},
      "body": {{ "x": 0.5, "y": 0.4 }},
      "cta": {{ "x": 0.5, "y": 0.8 }}
    }}
  }},
  "texts": [
    {{"id": "headline", "text": "Sample headline"}},
    {{"id": "body", "text": "Sample body text"}},
    {{"id": "cta", "text": "Sample CTA"}}
  ],
  "images": [
    {{"id": "image1", "desc": "A festive poster background with lights"}}
  ]
}}
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )

        assets_text = response.candidates[0].content.parts[0].text.strip()
        print("\n[DEBUG] Raw assets response:\n", assets_text)

        try:
            if assets_text.startswith("```"):
                assets_text = "\n".join(assets_text.split("\n")[1:-1])
            assets = json.loads(assets_text)
        except Exception as e:
            return jsonify({"error": f"Invalid JSON from LLM: {e}", "raw": assets_text}), 500

        # === SAFETY NET: Ensure styling block always exists ===
        default_styling = {
            "background": {"type": "color", "value": "#FFFFFF"},
            "fonts": {
                "headline": {"color": "#000000", "align": "center"},
                "body": {"color": "#333333", "align": "left"},
                "cta": {"color": "#FFFFFF", "align": "center"}
            },
            "layout": {
                "headline": {"x": 0.5, "y": 0.1},
                "body": {"x": 0.5, "y": 0.4},
                "cta": {"x": 0.5, "y": 0.8}
            }
        }

        styling = assets.get("styling") or default_styling

        # Generate actual image files
        generated_images = []
        for img in assets.get("images", []):
            img_id = img.get("id")
            img_desc = img.get("desc") or img.get("description")
            if not img_id or not img_desc:
                print(f"[WARNING] Skipping invalid image entry: {img}")
                continue
            img_path = generate_image_from_prompt(client, img_desc, img_id)
            generated_images.append({
                "id": img_id,
                "desc": img_desc,
                "path": img_path
            })

        # Merge into script
        scripts[script_id]["assets"] = {
            "styling": styling,
            "texts": assets.get("texts", []),
            "images": generated_images
        }
        save_scripts(scripts)

        return jsonify(scripts[script_id])

    return handler
