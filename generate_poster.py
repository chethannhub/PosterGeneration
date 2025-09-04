import os
import json
import subprocess
from flask import Flask, request, jsonify
from google import genai
from google.genai import types, errors
from utils import load_scripts, save_scripts, IMAGES_DIR, POSTER_DIR

MODEL = os.getenv("MODEL")

# Read Unity paths from environment with sensible defaults
UNITY_PATH = os.getenv("UNITY_PATH", r"C:\Program Files\Unity\Hub\Editor\2022.3.47f1\Editor\Unity.exe")
PROJECT_PATH = os.getenv("PROJECT_PATH", r"D:\Learn_unity\AdTemplate2D")

# Derived file paths inside the Unity project
CS_FILE_PATH = os.path.join(PROJECT_PATH, "Assets", "Editor", "PosterGenerator.cs")
LOG_FILE = os.path.join(PROJECT_PATH, "editor_log.txt")

os.makedirs(POSTER_DIR, exist_ok=True)
poster_abs_path = os.path.abspath(POSTER_DIR)

def generate_unity_script(client, script_data: dict):
    # Convert image paths to absolute paths
    for img in script_data["assets"]["images"]:
        img["path"] = os.path.abspath(img["path"])
    
    prompt = f"""
You are a senior Unity C# developer with extensive experience in creating editor scripts and Unity 2022.3 LTS.

Create a Unity editor script that:
1. Loads a background image without text
2. Places text at precise coordinates using TextMeshProUGUI
3. Renders the final composite in batch mode

Script data: {json.dumps(script_data, indent=2)}

Requirements:
1. Use TextMeshProUGUI for all text rendering with precise positioning
2. Load background images using Texture2D.LoadImage from absolute paths
3. Create a Canvas with RenderTexture for headless rendering  
4. Use normalized coordinates from layout data (0.0-1.0 range)
5. Convert normalized coords to pixel positions based on canvas size
6. Force canvas update with Canvas.ForceUpdateCanvases()
7. Render to RenderTexture and save as PNG

Generate a complete Unity C# script named PosterGenerator with method GeneratePoster():
- Class: public static class PosterGenerator
- Method: public static void GeneratePoster()
- Canvas size from styling.canvasSize (e.g., "1080x1350")
- Position text using layout array coordinates  
- Save final image to: {poster_abs_path}

Use only Unity 2022.3 LTS compatible APIs. No GUI functions. Provide only C# code.
"""
    
    # Log the prompt here so we can reproduce LLM outputs during debugging.
    print("[DEBUG] LLM Prompt:\n", prompt)
    
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        cs_code = response.candidates.content.parts.text
        
        # Clean up markdown formatting
        if cs_code.startswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[1:-1])
        if cs_code.endswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[:-1])
        
        # Ensure Unity namespaces
        if "using UnityEngine" not in cs_code:
            cs_code = "using UnityEngine;\nusing UnityEditor;\nusing System.IO;\nusing TMPro;\n\n" + cs_code
        
        return fix_unity_script(cs_code, client, script_data)
        
    except errors.ClientError as e:
        if e.status_code == 429:
            print("[WARNING] Gemini API quota exhausted.")
        else:
            raise

def fix_unity_script(cs_code, client, script_data: dict):
    # Convert image paths to absolute paths
    for img in script_data["assets"]["images"]:
        img["path"] = os.path.abspath(img["path"])
    
    prompt = f"""
Fix this Unity C# script for 2022.3 LTS batch mode compatibility:

{cs_code}

Requirements:
1. Use TextMeshProUGUI for text rendering
2. Create Canvas with Camera for RenderTexture rendering
3. Load background images with Texture2D.LoadImage()
4. Position text using normalized coordinates converted to pixels
5. Call Canvas.ForceUpdateCanvases() before rendering
6. Use RenderTexture.active and Camera.Render() for headless capture
7. Save PNG using File.WriteAllBytes()

Ensure:
- No compile errors
- Unity 2022.3 LTS compatible only
- Works in batch mode (-batchmode)
- Proper coordinate conversion from 0.0-1.0 to pixels
- Text positioning uses RectTransform.anchoredPosition

Provide only working C# code.
"""
    
    print("[DEBUG] LLM Prompt for fixing code:\n", prompt)
    
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        
        cs_code = response.candidates.content.parts.text
        
        # Clean up formatting
        if cs_code.startswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[1:])
        if cs_code.endswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[:-1])
        
        # Ensure Unity namespaces
        if "using UnityEngine" not in cs_code:
            cs_code = "using UnityEngine;\nusing UnityEditor;\nusing System.IO;\nusing TMPro;\n\n" + cs_code
        
        # Save the generated/fixed C# script into the Unity project's
        # Assets/Editor folder so Unity can compile and run it in batch mode.
        os.makedirs(os.path.dirname(CS_FILE_PATH), exist_ok=True)
        with open(CS_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(cs_code)

        print(f"[DEBUG] Unity C# script saved at: {CS_FILE_PATH}")
        return CS_FILE_PATH
        
    except errors.ClientError as e:
        if e.status_code == 429:
            print("[WARNING] Gemini API quota exhausted.")
        else:
            raise

def run_unity_batch():
    cmd = [
        UNITY_PATH,
        "-batchmode",
        "-projectPath", PROJECT_PATH,
        "-executeMethod", "PosterGenerator.GeneratePoster",
        "-quit",
        "-logFile", LOG_FILE
    ]
    
    print("[DEBUG] Command:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(f"[DEBUG] Unity Log file saved at: {LOG_FILE}")
    print(f"[DEBUG] Unity batchmode output: {result.stdout}\n{result.stderr}")
    
    return result.returncode == 0
