# PixelCloak Usage

## Backend
- Start: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Health: `GET /health`
- Cloak: `POST /cloak` with multipart `file`, form `mode=fast|balanced|strong`
- Response headers: `X-PixelCloak-Mode`, `X-PixelCloak-Steps`, `X-PixelCloak-Epsilon`, `X-PixelCloak-Time`

### Recommended Workflow
1. Upload PNG/JPEG (<=10MB). Backend converts to RGB.
2. Backend computes PGD perturbation on 224×224 CLIP space, upscales delta, applies to full-res, returns PNG.
3. Save PNG (do not reconvert to JPEG) to preserve the perturbation.

## Frontend
- Open `frontend_vanilla/index.html` (or serve via any static server).
- Drag/drop or browse images. Pick mode on the segmented control.
- Run "EXECUTE_CLOAKING_PROTOCOL"; download single files or batch ZIP.
- Use PREVIEW_CHANGE to see before/after and toggle 10× noise for verification.

## Modes (Research-backed)
- Fast: FGSM 1 step, ε=2/255 (visual safe, weakest)
- Balanced: PGD 10 steps, ε=4/255 (recommended balance)
- Strong: PGD 20 steps, ε=8/255 (may show slight artifacts)

## Performance
- CPU-only friendly. Torch + CLIP loads once on startup.
- First-time model pull (~600MB) from Hugging Face; cached after.
- Per-image runtime depends on resolution; 1–3s typical on modern CPU.
