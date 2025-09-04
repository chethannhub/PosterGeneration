import os
from google import genai
from flask import Flask, request, jsonify

from utils import POSTER_DIR, load_scripts  
from create_scripts_api import create_scripts
from generate_assets_api import generate_assets
from generate_poster import generate_unity_script, run_unity_batch

app = Flask(__name__)

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in environment variables")

client = genai.Client(api_key=GEMINI_API_KEY)
print("=== Gemini Client Initialized ===")

@app.route("/api/createScripts", methods=["POST"])
def create_scripts_api_route():
    """Fixed: Call the function directly"""
    print("Scripts API called")
    return create_scripts(client)  # Direct call, not nested function

@app.route("/api/generateAssets", methods=["POST"])  
def generate_assets_api_route():
    """Fixed: Call the function directly"""
    print("Assets API called")
    return generate_assets(client)  # Direct call, not nested function

@app.route("/api/generatePoster", methods=["POST"])
def generate_poster_api():
    print("Poster API called")
    
    data = request.json
    script_id = data.get("id")
    
    scripts = load_scripts()
    if script_id not in scripts:
        return jsonify({
            "error": "Invalid script ID", 
            "available": list(scripts.keys())
        }), 400
    
    script_data = scripts[script_id]
    
    # Check if assets exist
    if "assets" not in script_data:
        return jsonify({
            "error": "No assets found. Generate assets first."
        }), 400
    
    try:
        # Generate Unity script with layout positioning
        cs_file_path = generate_unity_script(client, script_data)
        print(f"[DEBUG] Unity script generated: {cs_file_path}")
        
        # Run Unity in batch mode
        success = run_unity_batch()
        
        if success:
            return jsonify({
                "success": True,
                "message": "Poster generated successfully",
                "poster_dir": POSTER_DIR,
                "script_path": cs_file_path
            })
        else:
            return jsonify({
                "error": "Unity batch execution failed",
                "poster_dir": POSTER_DIR
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": f"Failed to generate poster: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
