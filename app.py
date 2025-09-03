#app.py

import os
from google import genai
from flask import Flask
from flask import Flask, request, jsonify
from predefine_generate_poster import build_layout_and_assets, run_unity_with_spec
from utils import POSTER_DIR, load_scripts
from create_scripts_api import create_scripts
from generate_assets_api import generate_assets
from generate_poster import generate_unity_script, run_unity_batch


app = Flask(__name__)

# --- Gemini Client ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in environment variables")

client = genai.Client(api_key=GEMINI_API_KEY)

# --- API Routes ---
@app.route("/api/createScripts", methods=["POST"])
def create_scripts_api_route():
    print("\nCreate Scripts API called\n")
    return create_scripts(client)()

@app.route("/api/generateAssets", methods=["POST"])
def generate_assets_api_route():
    print("\nGenerate Assets API called\n")
    return generate_assets(client)()



@app.route("/api/generatePoster", methods=["POST"])
def generate_poster_api():
    print("\nGenerate poster api called\n")
    data = request.json
    script_id = data.get("id")
    SCRIPTS = load_scripts()

    if script_id not in SCRIPTS:
        return jsonify({"error": "Invalid script ID"}), 400

    cs_path = generate_unity_script(client, SCRIPTS[script_id])

    success = run_unity_batch()
    if success:
        return jsonify({"status": "Poster generated successfully", "cs_file": cs_path})
    else:
        return jsonify({"status": "Failed to generate poster, check Unity logs", "cs_file": cs_path}), 500

@app.route("/api/predefineGeneratePoster", methods=["POST"])
def build_poster():
    try:
        scripts = load_scripts()  
        
        scripts = {str(k): v for k, v in scripts.items()}
        
        data = request.get_json(force=True)
        script_id = str(data.get("id"))

        if script_id not in scripts:
            return jsonify({"status": "error", "msg": "Invalid script ID"}), 400

        script_info = scripts[script_id]

        poster_name = f"poster_{script_id}.png"
        poster_out_path = os.path.join(POSTER_DIR, poster_name)

        spec = build_layout_and_assets(script_info, poster_out_path, tmp_dir=os.path.join(POSTER_DIR, "tmp"))

        success = run_unity_with_spec(spec)

        if not success:
            return jsonify({"status": "error", "msg": "Unity failed"}), 500

        return jsonify({"status": "ok", "poster": poster_out_path})

    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
