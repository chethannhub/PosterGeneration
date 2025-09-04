# create_scripts_api.py
import os
import json
from flask import request, jsonify
from google.genai import types
from utils import load_scripts, save_scripts

MODEL = os.getenv("MODEL")
if not MODEL:
    raise RuntimeError("MODEL must be set in environment variables")


def create_scripts(client):
    """Generate 3 creative script variants using the LLM.

    This function:
    - Reads the incoming JSON request (product, description, size).
    - Prompts the LLM for three strict JSON script variants.
    - Parses and persists the returned scripts into `specs/scripts_data.json`.

    Keep error handling defensive: the LLM can return non-JSON or wrap the
    JSON in Markdown code fences. We attempt to strip common wrappers then
    fall back to a helpful error object stored in the specs so the UI can
    surface errors to the user.
    """
    scripts_store = load_scripts()

    data = request.json
    product = data.get("product", "Your Product")
    description = data.get("description", "Exclusive Offer")
    size = data.get("size", "1080x1350")

    # Prompt requests strict JSON. We still sanitize output below.
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

        # Strip common Markdown code fences if present
        if output_text.startswith("```"):
            output_text = output_text.strip().lstrip("`").rstrip("`")

        scripts_list = json.loads(output_text)

        if not isinstance(scripts_list, list):
            scripts_list = [scripts_list]

    except json.JSONDecodeError as e:
        # Keep raw output logged for debugging and persist an error object
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

    # Persist results (or error object) to specs
    for s in scripts_list:
        scripts_store[s["id"]] = s
    save_scripts(scripts_store)

    return jsonify(scripts_list)
