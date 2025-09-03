# new_generate_poster.py
import os
import json
import subprocess
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from utils import IMAGES_DIR, POSTER_DIR

UNITY_PATH = r"C:\Program Files\Unity\Hub\Editor\2022.3.47f1\Editor\Unity.exe"
PROJECT_PATH = r"D:\Learn_unity\AdTemplate2D"
LOG_FILE = os.path.join(PROJECT_PATH, "editor_log.txt")
SPEC_PATH = os.path.join("D:\\Learn_unity\\AdTemplate2D_Backend", "poster_spec.json")

os.makedirs(POSTER_DIR, exist_ok=True)

# ================== TEXT RENDERING ==================

def render_text_to_png(text, font_size, color, out_path, max_width=None, padding=8):
    """Render text to PNG with Pillow (no font family, just color+alignment)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # parse color
    if isinstance(color, str) and color.startswith("#"):
        hexv = color[1:]
        if len(hexv) == 6:
            color = tuple(int(hexv[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        elif len(hexv) == 8:
            color = tuple(int(hexv[i:i+2], 16) for i in (0, 2, 4, 6))
        else:
            raise ValueError("Bad color hex")

    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)

    # word wrap
    if max_width:
        words = text.split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            tw, _ = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), trial, font=font)[2:]
            if tw + 2 * padding <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        text = "\n".join(lines)

    # measure
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + 2 * padding
    h = bbox[3] - bbox[1] + 2 * padding

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.multiline_text((padding, padding), text, font=font, fill=color, spacing=int(font_size * 0.2))
    img.save(out_path)
    return out_path, w, h


# ================== LAYOUT BUILDER ==================

def build_layout_and_assets(script_data, poster_out_path, tmp_dir):
    """
    Convert high-level script_data (from JSON) into Unity spec.
    """
    os.makedirs(tmp_dir, exist_ok=True)

    # --- size ---
    size = script_data.get("size", "1080x1080")
    if isinstance(size, str) and "x" in size:
        w, h = map(int, size.lower().split("x"))
    else:
        raise ValueError(f"Invalid size format: {size}")

    layers = []

    # --- background ---
    bg = script_data["assets"]["styling"].get("background", {})
    if bg.get("type") == "color":
        bg_color = bg["value"]
        bg_img = os.path.join(tmp_dir, "background.png")

        # generate flat background PNG
        color = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5)) + (255,)
        Image.new("RGBA", (w, h), color).save(bg_img)
        layers.append({"path": os.path.abspath(bg_img), "x": 0, "y": 0,
                       "width": w, "height": h, "opacity": 1.0})

    # --- images ---
    for img in script_data["assets"].get("images", []):
        layers.append({
            "path": os.path.abspath(img["path"]),
            "x": int(w * 0.25),   
            "y": int(h * 0.25),
            "width": int(w * 0.5),
            "height": int(h * 0.5),
            "opacity": 1.0
        })

    # --- texts ---
    styling = script_data["assets"]["styling"]
    for i, txt in enumerate(script_data["assets"].get("texts", [])):
        style = styling["fonts"].get(txt["id"], {})
        layout = styling["layout"].get(txt["id"], {"x": 0.5, "y": 0.5})

        font_size = 64 if txt["id"] == "headline" else 36
        text_png = os.path.join(tmp_dir, f"text_{i:02d}.png")

        _, tw, th = render_text_to_png(
            text=txt["text"],
            font_size=font_size,
            color=style.get("color", "#FFFFFF"),
            out_path=text_png,
            max_width=w - 100,
        )

        # center alignment
        px = int(layout["x"] * w - tw / 2)
        py = int(layout["y"] * h - th / 2)

        layers.append({
            "path": os.path.abspath(text_png),
            "x": px,
            "y": py,
            "width": tw,
            "height": th,
            "opacity": 1.0
        })

    spec = {
        "size": {"width": int(w), "height": int(h)},
        "layers": layers,
        "outputPath": os.path.abspath(poster_out_path)
    }
    return spec


# ================== UNITY CALL ==================

def run_unity_with_spec(spec):
    """Write spec JSON and call Unity in batchmode."""
    os.makedirs(os.path.dirname(SPEC_PATH), exist_ok=True)
    with open(SPEC_PATH, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)

    env = os.environ.copy()
    env["POSTER_SPEC"] = SPEC_PATH

    cmd = [
        UNITY_PATH,
        "-batchmode",
        "-projectPath", PROJECT_PATH,
        "-executeMethod", "PredefinedPosterGenerator.GeneratePoster",
        "-quit",
        "-logFile", LOG_FILE
    ]
    print("\n[DEBUG] Command:\n", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    print(f"[DEBUG] Unity Log file saved at {LOG_FILE}")
    print(f"[DEBUG] Unity batchmode output:\n{result.stdout}\n{result.stderr}")
    return result.returncode == 0
