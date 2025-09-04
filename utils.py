import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# --- Paths (configurable via .env) ---
SCRIPTS_FILE = os.getenv("SCRIPTS_FILE", "specs/scripts_data.json")
IMAGES_DIR = os.getenv("IMAGES_DIR", "generated_images")
POSTER_DIR = os.getenv("POSTER_DIR", "posters")

# Ensure directories exist
Path(os.path.dirname(SCRIPTS_FILE) or ".").mkdir(parents=True, exist_ok=True)
Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
Path(POSTER_DIR).mkdir(parents=True, exist_ok=True)


# --- Persistence Helpers ---
def load_scripts():
    if os.path.exists(SCRIPTS_FILE):
        with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
            scripts = json.load(f)
        # ensure keys are ints when possible
        try:
            return {int(k): v for k, v in scripts.items()}
        except Exception:
            return scripts
    return {}


def save_scripts(scripts_dict):
    with open(SCRIPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(scripts_dict, f, indent=4)
