# PixelCloak

CPU-only adversarial image cloaking tool using **CLIP-driven PGD attacks** to disrupt feature-space alignment in diffusion-style models (Stable Diffusion, DALL-E, Midjourney fine-tuning).

The attack uses **negated cosine similarity** on L2-normalised CLIP ViT-B/32 features as the loss function. The PGD loop iteratively perturbs image pixels to maximise the distance between the adversarial and original CLIP embeddings, making it harder for downstream models to learn your likeness.

## Features

- **FastAPI backend** with CLIP `openai/clip-vit-base-patch32` surrogate model
- **Three attack modes**: Fast (FGSM 1-step), Balanced (PGD 10-step), Strong (PGD 20-step)
- **CPU-only** — no GPU required. Perturbation computed at 224×224, upscaled to original resolution
- **PNG output** with rich response headers: mode, steps, epsilon, time, max/mean pixel delta
- **Rate limiting** (slowapi) and magic-byte file validation for security
- **Elite cyberpunk frontend**: matrix rain, glitch text, glassmorphism, comparison slider, ambient audio
- **verify_poison.py**: CLI tool with CLIP cosine similarity measurement and JSON output

## Quickstart

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### macOS (zsh)
```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Linux (bash)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open `frontend_vanilla/index.html` in your browser (or serve it with any static file server).

### Custom API URL

By default the frontend connects to `http://localhost:8000`. To point it at a different server, add this script tag in `index.html` **before** `app.js`:

```html
<script> window.PIXELCLOAK_API_URL = 'https://your-server.com'; </script>
```

### CORS Configuration

By default, the backend allows origins `http://localhost:8000` and `http://127.0.0.1:8000`. To override for production, set the environment variable:

```bash
export PIXELCLOAK_ALLOWED_ORIGINS="https://your-domain.com,https://www.your-domain.com"
```

## API

### `GET /health`
Returns `{ "status": "healthy", "model_loaded": true, "device": "cpu" }`

### `POST /cloak`
- **Body**: multipart form — `file` (image), `mode` (fast | balanced | strong)
- **Response**: PNG image bytes
- **Rate limit**: 10 requests/minute per IP

#### Response Headers

| Header | Description |
|---|---|
| `X-PixelCloak-Mode` | Attack mode used |
| `X-PixelCloak-Steps` | Number of PGD iterations |
| `X-PixelCloak-Epsilon` | Perturbation budget (0–255 scale) |
| `X-PixelCloak-Time` | Processing time |
| `X-PixelCloak-MaxDelta` | Maximum per-pixel shift (0–255) |
| `X-PixelCloak-MeanDelta` | Mean absolute per-pixel shift (0–255) |

## Modes

| Mode | Algorithm | Steps | ε (0–255) | Notes |
|---|---|---|---|---|
| Fast | FGSM | 1 | 2.0 | Fastest, weakest protection |
| Balanced | PGD | 10 | 4.0 | Recommended default |
| Strong | PGD | 20 | 8.0 | Strongest, may show visible artifacts |

## Loss Function

The attack minimises:

```
loss = -cosine_similarity(CLIP(adversarial), CLIP(original))
```

This pushes the adversarial image's CLIP embedding **away** from the original, disrupting any model that uses CLIP-family encoders for conditioning or fine-tuning.

## Verify Poison Script

```bash
# Basic usage
python verify_poison.py original.png cloaked.png

# Custom amplification and output path
python verify_poison.py original.png cloaked.png --amplify 100 --output diff.png

# Measure CLIP embedding disruption (most useful metric)
python verify_poison.py original.png cloaked.png --compare-clip

# Machine-readable JSON output
python verify_poison.py original.png cloaked.png --compare-clip --json
```

## Known Limitations

1. **JPEG fragility**: JPEG compression destroys adversarial perturbations. Always save and share cloaked images as **PNG**.
2. **Diffusion purification**: Running a cloaked image through img2img with low denoise strength can neutralise perturbations.
3. **CLIP ≠ VAE transfer gap**: PixelCloak attacks CLIP's visual encoder, but Stable Diffusion's VAE encoder is a different network. While there is transfer (CLIP guides the diffusion process), the protection is not absolute against all model architectures.
4. **Resolution scaling**: Perturbations are computed at 224×224 and bilinearly upscaled. Very high-resolution images may have weaker per-pixel signal.
5. **Adversarial robustness**: This is a deterrent for naive scraping, **not** a cryptographic guarantee. Communicate this honestly to users.

## Project Layout

```
backend/              FastAPI + CLIP PGD engine
  main.py             API server with attack logic
  requirements.txt    Python dependencies
frontend_vanilla/     Static HTML/JS/CSS UI
  index.html          Page structure
  style.css           Visual design system
  app.js              Application logic
docs/                 Supplemental documentation
  USAGE.md            Detailed usage guide
  SECURITY_NOTES.md   Security model and expectations
verify_poison.py      CLI verification utility
```

## License

Not specified by the project owner.
