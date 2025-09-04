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
    # Add explicit instruction to exclude text from image generation
    text_free_prompt = f"{prompt}. IMPORTANT: Generate image without any text, letters, words, or typography. Pure complete visual elements only."
    
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=text_free_prompt)])],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        )
    )
    
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            data_buffer = part.inline_data.data
            file_extension = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
            img_path = os.path.join(IMAGES_DIR, f"{img_id}{file_extension}")
            save_binary_file(img_path, data_buffer)
            return img_path
    
    print(f"[WARNING] No image data returned for prompt: {prompt}")
    return None

def generate_assets(client):
    """Fixed: Direct function call, no nested handler"""
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
    
    # Modified prompt to generate layout coordinates and text-free images
    prompt = f"""
You are a creative ad poster assistant specializing in layout design.

Generate ONLY the assets section for this campaign:
Product: {script_info['product']}
Size: {script_info['size']}  
Script: {script_info['script']}
Tagline: {script_info.get('tagline', '')}

IMPORTANT: 
1. Image descriptions must NOT contain any text, words, letters, or typography
2. Provide precise layout coordinates for text placement
3. Use normalized coordinates (0.0 to 1.0) where (0,0) is top-left, (1,1) is bottom-right
4. Generate only one full image without text on the image

Return JSON strictly in this format (no explanations, no markdown):
{{
  "layout": [
    {{
      "id": "headline",
      "text": "Holiday Cookie Chaos!",
      "x": 0.5,
      "y": 0.15,
      "width": 0.8,
      "height": 0.1,
      "fontSize": 72,
      "color": "#FFFFFF",
      "fontWeight": "bold",
      "alignment": "center",
      "anchor": "middle-center"
    }},
    {{
      "id": "body",
      "text": "Limited time festive flavors",
      "x": 0.5,
      "y": 0.4,
      "width": 0.7,
      "height": 0.2,
      "fontSize": 32,
      "color": "#FFFFFF",
      "fontWeight": "normal", 
      "alignment": "center",
      "anchor": "middle-center"
    }},
    {{
      "id": "cta",
      "text": "Get Yours Before They're Gone!",
      "x": 0.5,
      "y": 0.85,
      "width": 0.6,
      "height": 0.08,
      "fontSize": 48,
      "color": "#000000",
      "fontWeight": "bold",
      "alignment": "center",
      "anchor": "middle-center"
    }}
  ],
  "images": [
    {{
      "id": "background",
      "desc": "Festive Christmas bakery background with warm colors, holiday decorations, cookie shapes, no text or letters visible"
    }}
  ],
  "styling": {{
    "backgroundColor": "#8B0000",
    "canvasSize": "{script_info['size']}"
  }}
}}
"""
    
    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
    )
    
    # FIX: Correct way to access the response
    assets_text = response.candidates[0].content.parts[0].text.strip()
    print("\n[DEBUG] Raw assets response:\n", assets_text)
    
    try:
        if assets_text.startswith("```"):
            assets_text = "\n".join(assets_text.split("\n")[1:-1])
        assets = json.loads(assets_text)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON from LLM: {e}", "raw": assets_text}), 500
    
    # Generate text-free images
    generated_images = []
    for img in assets.get("images", []):
        img_id = img.get("id")
        img_desc = img.get("desc") or img.get("description")
        
        if not img_id or not img_desc:
            print(f"[WARNING] Skipping invalid image entry: {img}")
            continue
        
        print(f"[DEBUG] Generating image for: {img_desc}")
        img_path = generate_image_from_prompt(client, img_desc, img_id)
        generated_images.append({
            "id": img_id,
            "desc": img_desc,
            "path": img_path
        })
    
    # Store layout and images in script
    scripts[script_id]["assets"] = {
        "layout": assets.get("layout", []),
        "images": generated_images,
        "styling": assets.get("styling", {})
    }
    
    save_scripts(scripts)
    return jsonify(scripts[script_id])
