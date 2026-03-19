# PixelCloak

CPU-only image cloaking tool using CLIP-driven PGD perturbations to disrupt feature alignment in diffusion-style models (Stable Diffusion, DALL-E). Frontend is vanilla JS with animated cyberpunk UI.

## Features
- FastAPI backend with CLIP `openai/clip-vit-base-patch32` surrogate.
- Three modes on `/cloak`: Fast (FGSM 1 step), Balanced (PGD 10 steps), Strong (PGD 20 steps).
- PNG output with exposed headers (`X-PixelCloak-Mode`, `-Steps`, `-Epsilon`, `-Time`).
- CPU-only friendly: perturbation computed at 224×224 then upscaled to original size.
- Frontend: drag-drop uploader, animated mode selector, before/after slider, 10× noise visualization, JSZip batch download.

## Quickstart
1. Create/activate virtualenv (example PowerShell):
   ```powershell
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
   ```
2. Install deps:
   ```powershell
   pip install -r backend/requirements.txt
   ```
3. Run backend:
   ```powershell
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
4. Open `frontend_vanilla/index.html` in a browser (or serve statically); ensure CORS allows `localhost:8000`.

## API
- `GET /health` → `{ status, model_loaded, device }`
- `POST /cloak` (multipart `file`, form `mode=fast|balanced|strong`) → PNG bytes, headers with mode/epsilon/steps/time

## Modes
- Fast: 1 step FGSM, ε=2/255
- Balanced: 10 step PGD, ε=4/255
- Strong: 20 step PGD, ε=8/255

## Notes & Limitations
- Perturbations are fragile against JPEG compression and diffusion "purification"; advertise honestly to users.
- Keep outputs as PNG to preserve noise.
- First run downloads CLIP (~600MB) after torch install.

## Frontend Tips
- Hard-refresh to pick up CSS/JS changes.
- Use the comparison modal to inspect perturbations; toggle 10× noise to verify presence.

## Project Layout
- `backend/` FastAPI + CLIP PGD engine
- `frontend_vanilla/` Static HTML/JS/CSS UI
- `docs/` Supplemental usage and security notes
- `verify_poison.py` Utility script (if present) for local checks

## License
Not specified by the project owner.
