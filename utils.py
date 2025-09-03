import os
import json

# --- Paths ---
SCRIPTS_FILE = "specs/scripts_data.json"
IMAGES_DIR = "generated_images"
POSTER_DIR = "posters"

os.makedirs(IMAGES_DIR, exist_ok=True)

# --- Persistence Helpers ---
def load_scripts():
    if os.path.exists(SCRIPTS_FILE):
        scripts = json.load(open(SCRIPTS_FILE))
        # ensure keys are ints
        return {int(k): v for k, v in scripts.items()}
    return {}

def save_scripts(scripts_dict):
    with open(SCRIPTS_FILE, "w") as f:
        json.dump(scripts_dict, f, indent=4)
