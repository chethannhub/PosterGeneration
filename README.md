## PosterGeneration — 2D Ad Template Generator

A backend tool that uses GenAI + Unity to automatically create 2D ad/poster samples from a short product or brand description to achive deterministic.

Key features
- Generate 3 distinct script/creative directions from a single short brief.
- Produce text-free image assets and a layout plan using GenAI.
- Emit a Unity C# Editor script and run Unity in batch mode to render PNG posters.
- Built for reproducibility: deterministic prompts and saved specs allow reliable re-runs.

Repository layout (important files/directories)
- `app.py` — Flask app exposing API endpoints
- `create_scripts_api.py` — calls LLM to create 3 script variants and saves to `specs/scripts_data.json`
- `generate_assets_api.py` — uses LLM to produce layout + image prompts, generates text-free images into `generated_images/`
- `generate_poster.py` — uses LLM to produce a Unity C# editor script, saves it to the Unity project, then runs Unity in batch mode to render posters into `posters/`
- `utils.py` — helper functions and path constants


Prerequisites
- Python 3.10+ (Windows)
- Unity 2022.3 LTS installed for authoring and batch rendering
- A Google GenAI-compatible client library and API key (the code uses `google.genai`)

Environment variables
- `GEMINI_API_KEY` — API key used by `google.genai` client
- `MODEL` — text model id for script/layout generation
- `IMAGE_MODEL` — image model id for text-free image generation

Setup (PowerShell / pwsh.exe)
1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Set required environment variables (example, replace values)

```powershell
$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
$env:MODEL = "models/text-model-id"
$env:IMAGE_MODEL = "models/image-model-id"
```

Run the backend

```powershell
python .\app.py
```

API endpoints and PowerShell examples
All API calls below assume the Flask backend is running locally at `http://127.0.0.1:5000`.

1) Create scripts (returns 3 script variants)

```powershell
$body = @{ product = 'Doughpocalypse'; description = 'Three festive cookie flavors'; size = '1080x1350' }
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/createScripts' -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json)
```

Response: JSON array with objects like `{ id, title, script, tagline, product, size }`.

2) Generate assets for a script (images + layout)

```powershell
$body = @{ id = 1 }
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/generateAssets' -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json)
```

This writes text-free images into `generated_images/` and updates `specs/scripts_data.json` adding an `assets` section for the script.

3) Generate poster (Unity batch render)

```powershell
$body = @{ id = 1 }
Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/generatePoster' -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json)
```

On success the endpoint returns `poster_dir` and `script_path`. The Unity Editor script is saved under your Unity project (see `generate_poster.py` for `CS_FILE_PATH`). Unity is invoked in batch mode to run `PosterGenerator.GeneratePoster` which should render and save a PNG into `posters/`.

Unity setup notes
- Ensure Unity 2022.3.47 LTS is installed and project setuped with 2D Universal render pipeline
- The `UNITY_PATH` and `PROJECT_PATH` constants in `generate_poster.py` point to the correct Unity Editor path and your Unity project location.
- The code expects a Unity project at `PROJECT_PATH` with `Assets/Editor/` writable — the script saves `PosterGenerator.cs` there.
- Text rendering uses TextMeshPro (the generated script uses `TextMeshProUGUI`). Make sure TextMeshPro is available in the project (Install thourgh Package Manager).
- Headless rendering requires the Unity project to be able to render in batch mode without manual setup; test once from Editor to iterate quickly.





