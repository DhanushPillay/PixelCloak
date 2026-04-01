# PixelCloak

Adversarial image cloaking tool using **ensemble CLIP/SigLIP** + **Momentum Iterative FGSM (MI-FGSM)** with optional **Expectation over Transformation (EoT)** to disrupt feature-space alignment in diffusion-style models and multimodal LLMs.

The attack supports **Targeted Image-to-Image Feature Collision**, maximizing the cosine similarity between the adversarial image and a distinct target image (or default cryptographic noise), computed natively at full resolution to survive advanced tile-scaling bypasses used by commercial AIs.

## Features

- **Targeted Feature Collision**: Directly targets custom uploaded image features or a localized cryptographic noise default (`assets/default_target.png`).
- **Native Resolution Gradients**: Computes the backward pass directly on the full-resolution image instead of a 224x224 thumbnail, shattering commercial AI tile-grid upscaling filters (e.g., GPT-4o, Claude).
- **FastAPI backend** attacking a **diverse ensemble**: `openai/clip-vit-base-patch32`, `openai/clip-vit-large-patch14`, `google/siglip-base-patch16-224`
- **MI-FGSM** with momentum + **edge-aware epsilon** and optional **EoT (JPEG-ish noise, resize, blur)** for robust transferability
- **Three attack modes**: Fast (FGSM 1-step), Balanced (PGD 10-step), Strong (PGD 20-step)
- **LPIPS regularisation** to keep perturbations imperceptible; PNG output with rich headers
- **Rate limiting** (slowapi) and magic-byte file validation for security
- **Frontend**: matrix rain, glitch text, glassmorphism, comparison slider, ambient audio
- **Verification CLI**: `tools/verify_poison.py` with CLIP/SigLIP cosine similarity and JSON output

## Quickstart

### Windows (PowerShell)
```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### macOS (zsh)
```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Linux (bash)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open `frontend_vanilla/index.html` in your browser (or serve it with any static file server). Use the **USE_EOT_ROBUSTNESS** toggle for transferability.

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
Returns `{ "status": "healthy", "models_loaded": 3, "device": "cpu"|"cuda" }`

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

The engine computes gradients natively across the full-resolution target, resolving commercial AI chunking bypasses. The attack primarily relies on **Image-to-Image Feature Collision**:

```
loss = +cosine_similarity(Ensemble(adversarial), Ensemble(target_image))
```

If left unassigned, this forces the AI to "hallucinate" cryptographic random noise (`assets/default_target.png`) instead of parsing your image. If users upload a custom file (e.g., a garbage truck), the image mathematically aligns with that secondary object across all latent variables.

## Verify Poison Script

```bash
# Basic usage
python tools/verify_poison.py original.png cloaked.png

# Custom amplification and output path
python tools/verify_poison.py original.png cloaked.png --amplify 100 --output diff.png

# Measure CLIP embedding disruption (most useful metric)
python tools/verify_poison.py original.png cloaked.png --compare-clip

# Machine-readable JSON output
python tools/verify_poison.py original.png cloaked.png --compare-clip --json

# Cross-model robustness check (CLIP-B/L + SigLIP)
python tools/verify_poison.py original.png cloaked.png --compare-all
```

## Known Limitations

1. **JPEG fragility**: JPEG compression destroys adversarial perturbations. Always save and share cloaked images as **PNG**.
2. **Diffusion purification**: Running a cloaked image through img2img with low denoise strength can neutralise perturbations.
3. **CLIP ≠ VAE transfer gap**: PixelCloak attacks CLIP's visual encoder, but Stable Diffusion's VAE encoder is a different network. While there is transfer (CLIP guides the diffusion process), the protection is not absolute against all model architectures.
4. **Resolution scaling**: Perturbations are computed at 224×224 and bilinearly upscaled. Very high-resolution images may have weaker per-pixel signal.
5. **Adversarial robustness**: This is a deterrent for naive scraping, **not** a cryptographic guarantee. Communicate this honestly to users.

## Project Layout

```
README.md             Project overview (only file in root)
assets/
  samples/            Example images (moved out of root)
backend/              FastAPI + ensemble adversarial engine
  main.py             API server bootstrap
  requirements.txt    Python dependencies
frontend_vanilla/     Static HTML/JS/CSS UI
docs/                 Supplemental documentation
  USAGE.md            Detailed usage guide
  SECURITY_NOTES.md   Security model and expectations
tools/
  verify_poison.py    CLI verification utility
```

## License

Not specified by the project owner.
