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
    def handler():
        SCRIPTS = load_scripts()
        data = request.json
        product = data.get("product", "Your Product")
        description = data.get("description", "Exclusive Offer")
        size = data.get("size", "1080x1350")

        prompt = f"""
        You are an expert ad copywriter.
        Generate 3 poster script options for a festival promotion.

        Product: {product}
        Description: {description}
        Size: {size}

        Return strictly as JSON array:
        [
          {{
            "id": 1,
            "title": "...",
            "script": "...",
            "tagline": "...",
            "product": "{product}",
            "size": "{size}",
            }}

        ]
        """

        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )

        output_text = response.candidates[0].content.parts[0].text
        try:
            scripts_list = json.loads(output_text.strip("`json\n "))
        except Exception as e:
            scripts_list = [{"id": 0, "title": "Error", "script": str(e), "tagline": ""}]

        # Save to persistent storage
        for s in scripts_list:
            SCRIPTS[s["id"]] = s
        save_scripts(SCRIPTS)

        return jsonify(scripts_list)

    return handler
