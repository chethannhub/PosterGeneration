# generate_poster.py

import os
import json
import subprocess
from flask import Flask, request, jsonify
from google import genai
from google.genai import types, errors
from utils import load_scripts, save_scripts, IMAGES_DIR, POSTER_DIR

MODEL = os.getenv("MODEL")
UNITY_PATH = r"C:\Program Files\Unity\Hub\Editor\2022.3.47f1\Editor\Unity.exe"
PROJECT_PATH = r"D:\Learn_unity\AdTemplate2D"
CS_FILE_PATH = os.path.join(PROJECT_PATH, "Assets", "Editor", "PosterGenerator.cs")
LOG_FILE = os.path.join(PROJECT_PATH, "editor_log.txt")


os.makedirs(POSTER_DIR, exist_ok=True)

poster_abs_path = os.path.abspath(POSTER_DIR)

def generate_unity_script(client, script_data: dict):
    
    for img in script_data['assets']['images']:
        img['path'] = os.path.abspath(img['path'])

    prompt = f"""
        You are a senior Unity C# developer with extensive experience in creating editor scripts and Unity 2022.3 LTS. 
        You need to make poster by using given json script data, if mutiple images was there pls arrange them as per the instruction.
        Generate a complete, compile-ready Unity editor script named PosterGenerator.cs
        for Unity 2022.3 LTS that runs in batch mode (headless).  
        This is json data: {script_data}

        Requirements:

        1. Do NOT use GUI.Label, EditorGUI, OnGUI, or any GUI functions.
        2. Only use APIs, methods, classes, and namespaces that exist in Unity 2022.3 LTS and work in batch mode.
        3. Render all text and images directly onto a RenderTexture or Texture2D using batch-safe methods:
        - For images: use Texture2D.LoadImage from absolute paths and Graphics.DrawTexture or SetPixels.
        - For text: either use TextMeshProUGUI in a temporary hidden Canvas + Camera, or simple bitmap fonts without shaders.
        4. Avoid any methods that don't exist in Unity 2022.3 LTS (e.g., CommitStyles).
        5. Ensure helper methods have correct argument counts and exist.
        6. Include Debug.Log statements for every step.
        7. Avoid overlapping UI elements; anchor and position images and texts properly.
        8. Always cross-check using directives.
        9. Stick to namespaces that exist in Unity 2022.3 LTS, such as UnityEngine, UnityEditor, System.IO, etc.
        10. In batch or headless mode Unity executes everything in a single frame without the normal update loop.
            If the UI system has not finished a layout pass and the camera never writes to the RenderTexture ReadPixels simply captures a solid background colour, producing a blank PNG.
            1. Force the canvas system to build meshes and layout once
            Canvas.ForceUpdateCanvases();         

            2.Make sure we read from the RT the camera will render into
            RenderTexture.active = renderTexture; 

            3. Render one frame **after** everything is ready
            renderCamera.Render();                

        Script specifics:

        - Class: PosterGenerator
        - Method: public static void GeneratePoster()
        - Load images from absolute paths: {[img['path'] for img in script_data['assets']['images']]}
        - Apply texts: {script_data['assets']['texts']}
        - Apply styles/colors/fonts/effects: {script_data['assets']['styling']}
        - Poster resolution: {script_data['size']}
        - Save the final poster as PNG to: {poster_abs_path}
        - All methods must be static, public, and fully functional.
        - Ensure all images and texts are correctly applied in their positions.

        Constraints:
        - JSON only for your reference to generate the code
        - Don't Hardcoded JSON or add filters, you shouldn't embed JSON directly in the code
        - Fix these escapes in your input JSON string before parsing in Unity.
            - Internal double-quotes inside strings that are not escaped
            - Incorrect backslash escaping in file paths
        - No compile errors.
        - Use only valid APIs, methods, classes, and namespaces that exist in Unity 2022.3 LTS and work in batch mode.
        - Batch mode compatible.
        - Provide only C# code; do not include explanations or markdown fences.
    """


    print("\n[DEBUG] LLM Prompt: \n", prompt)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        cs_code = response.candidates[0].content.parts[0].text

        if cs_code.startswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[1:])
        if cs_code.endswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[:-1])

        # Ensure Unity namespaces
        if "using UnityEngine;" not in cs_code:
            cs_code = "using UnityEngine;\nusing UnityEditor;\n" + cs_code

        fix_unity_script(cs_code, client, script_data)

    except errors.ClientError as e:
        if e.status_code == 429:
            print("\n[WARNING] Gemini API quota exhausted.\n")

        else:
            raise

# --- Execute Unity batchmode to run the script ---
def fix_unity_script(csCode, client, script_data: dict):
    
    for img in script_data['assets']['images']:
        img['path'] = os.path.abspath(img['path'])

    prompt = f"""
     You are a senior Unity C# developer with extensive experience in creating editor scripts and Unity 2022.3 LTS. 
     
     In this c# code, fix the errors if any are there
    
    {csCode}
    
    Fix the following Unity C# script to ensure it adheres to the specified requirements and constraints:
    
       Requirements:

        1. Do NOT use GUI.Label, EditorGUI, OnGUI, or any GUI functions.
        2. Only use APIs, methods, classes, and namespaces that exist in Unity 2022.3 LTS and work in batch mode.
        3. Render all text and images directly onto a RenderTexture or Texture2D using batch-safe methods:
        - For images: use Texture2D.LoadImage from absolute paths and Graphics.DrawTexture or SetPixels.
        - For text: either use TextMeshProUGUI in a temporary hidden Canvas + Camera, or simple bitmap fonts without shaders.
        4. Avoid any methods that don't exist in Unity 2022.3 LTS (e.g., CommitStyles).
        5. Ensure helper methods have correct argument counts and exist.
        8. Always cross-check using directives.
        9. Stick to namespaces that exist in Unity 2022.3 LTS, such as UnityEngine, UnityEditor, System.IO, etc.

        Constraints:
        - JSON only for your reference to generate the code
        - Don't Hardcoded JSON or add filters, you shouldn't embed JSON directly in the code
        - Internal double-quotes inside strings that are not escaped
            Incorrect backslash escaping in file paths
            Fix these escapes in your input JSON string before parsing in Unity.
        - No compile errors.
        - Use only valid APIs, methods, classes, and namespaces that exist in Unity 2022.3 LTS and work in batch mode.
        - Batch mode compatible.
        - Provide only C# code; do not include explanations or markdown fences.

    """

    print("\n\n\n[DEBUG] LLM Prompt for fixing the c# code: \n", prompt)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])]
        )
        cs_code = response.candidates[0].content.parts[0].text

        if cs_code.startswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[1:])
        if cs_code.endswith("```"):
            cs_code = "\n".join(cs_code.split("\n")[:-1])

        # Ensure Unity namespaces
        if "using UnityEngine;" not in cs_code:
            cs_code = "using UnityEngine;\nusing UnityEditor;\n" + cs_code

        # Save C# script in Unity project Editor folder
        os.makedirs(os.path.dirname(CS_FILE_PATH), exist_ok=True)
        with open(CS_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(cs_code)

        print(f"\n[DEBUG] Unity C# script saved at {CS_FILE_PATH}\n")
        
        return CS_FILE_PATH

    except errors.ClientError as e:
        if e.status_code == 429:
            print("\n[WARNING] Gemini API quota exhausted.\n")

        else:
            raise

# --- Execute Unity batchmode to run the script ---
def run_unity_batch():
    cmd = [
        UNITY_PATH,
        "-batchmode",
        "-projectPath", PROJECT_PATH,
        "-executeMethod", "PosterGenerator.GeneratePoster",
        "-quit",
        "-logFile", LOG_FILE
    ]

    print("[DEBUG] Command:")
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"[DEBUG] Unity Log file saved at {LOG_FILE}")
    print(f"[DEBUG] Unity batchmode output:\n{result.stdout}\n{result.stderr}")
    return result.returncode == 0
