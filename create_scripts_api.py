#create_scripts_api.py
import os
import json
from flask import request, jsonify
from google.genai import types
from utils import load_scripts, save_scripts

MODEL = os.getenv("MODEL")
if not MODEL:
    raise RuntimeError("MODEL must be set in environment variables")

def create_scripts(client):
    """Fixed: Direct function call, not nested handlers"""
    SCRIPTS = load_scripts()
    
    data = request.json
    product = data.get("product", "Your Product")
    description = data.get("description", "Exclusive Offer")
    size = data.get("size", "1080x1350")
    
    prompt = f"""
You are an expert ad copywriter for holiday campaigns.
Generate 3 poster script options for a festive promotion.

Product: {product}
Description: {description}
Size: {size}

Return strictly as JSON array (no markdown, no backticks):
[
  {{
    "id": 1,
    "title": "First Campaign Title",
    "script": "Main ad copy text here",
    "tagline": "Catchy tagline",
    "product": "{product}",
    "size": "{size}"
  }},
  {{
    "id": 2,
    "title": "Second Campaign Title", 
    "script": "Different ad copy approach",
    "tagline": "Another tagline",
    "product": "{product}",
    "size": "{size}"
  }},
  {{
    "id": 3,
    "title": "Third Campaign Title",
    "script": "Third variation of copy",
    "tagline": "Final tagline option",
    "product": "{product}",
    "size": "{size}"
  }}
]
"""
    
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        output_text = response.candidates[0].content.parts[0].text.strip()
        print(f"[DEBUG] LLM Response: {output_text}")
        
        # Clean up any markdown formatting
        if output_text.startswith("```"):
            output_text = output_text.replace("```json", "").replace("```", "")
        elif output_text.startswith("```"):
            output_text = output_text.replace("```", "")

        scripts_list = json.loads(output_text)
        
        # Ensure scripts_list is actually a list
        if not isinstance(scripts_list, list):
            scripts_list = [scripts_list]
            
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parsing failed: {e}")
        print(f"[ERROR] Raw output: {output_text}")
        scripts_list = [{
            "id": 1, 
            "title": "Error in Generation", 
            "script": f"Failed to parse LLM output: {str(e)}", 
            "tagline": "Please try again",
            "product": product,
            "size": size
        }]
    except Exception as e:
        print(f"[ERROR] General error: {e}")
        scripts_list = [{
            "id": 1, 
            "title": "Error", 
            "script": str(e), 
            "tagline": "",
            "product": product,
            "size": size
        }]
    
    # Save to persistent storage
    for s in scripts_list:
        SCRIPTS[s["id"]] = s
    save_scripts(SCRIPTS)
    
    return jsonify(scripts_list)
