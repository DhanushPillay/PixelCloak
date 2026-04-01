# PixelCloak Usage Guide

## Backend

### Starting the Server
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### `GET /health`
Returns server status and model state.

#### `POST /cloak`
Multipart form upload with:
- `file` — main image file (PNG/JPEG, ≤10MB)
- `mode` — `fast` | `balanced` (default) | `strong`
- `target_image` (Optional) — custom target image for Feature Collision (e.g., photo of noise or a garbage can).
- `target_prompt` (Optional) — custom text prompt to push AI embeddings towards.
- `use_robustness` (Optional) — activates Expectation over Transformation simulating compression noise.

**Response**: PNG image bytes with metadata headers.

#### Response Headers

| Header | Example | Description |
|---|---|---|
| `X-PixelCloak-Mode` | `balanced` | Attack mode used |
| `X-PixelCloak-Steps` | `10` | PGD iteration count |
| `X-PixelCloak-Epsilon` | `4.0` | Perturbation budget |
| `X-PixelCloak-Time` | `2.34s` | Processing duration |
| `X-PixelCloak-MaxDelta` | `4.12` | Max pixel shift (0–255) |
| `X-PixelCloak-MeanDelta` | `0.89` | Mean pixel shift (0–255) |

### Recommended Workflow
1. Upload PNG or JPEG (≤10MB) in the UI. 
2. Add a `CUSTOM TARGET IMAGE` object (strongly recommended: a photo of garbage or an empty wall). If you do not attach one, PixelCloak mathematically defaults to `assets/default_target.png` (built-in algorithmic noise).
3. Backend computes PGD perturbation on latent features natively.
4. Response is a cloaked PNG. **Do not re-encode to JPEG** — this destroys the perturbation. Ensure EoT Robustness is ON for chatbots!

### Rate Limiting
The `/cloak` endpoint is rate-limited to **10 requests per minute per IP** via slowapi. Exceeding this returns HTTP 429.

### CORS Configuration
By default, CORS allows `http://localhost:8000` and `http://127.0.0.1:8000`. Override via environment variable:
```bash
export PIXELCLOAK_ALLOWED_ORIGINS="https://app.example.com,https://api.example.com"
```

---

## Frontend

### Setup
Open `frontend_vanilla/index.html` directly in a browser, or serve via any static server.

### Custom API URL
By default, the frontend connects to `http://localhost:8000`. To configure a different backend:
```html
<!-- Add before app.js in index.html -->
<script> window.PIXELCLOAK_API_URL = 'https://your-server.com'; </script>
```

### Features
- Drag-and-drop or browse to upload images
- 3-mode selector with animated switching (Fast/Balanced/Strong)
- Real-time processing timer and file counter
- Response metadata display (mode, epsilon, steps, time, max/mean delta)
- Before/after comparison slider (mouse, touch, and keyboard: ←/→ arrows, Escape)
- 10× noise amplification toggle
- SAVE_DIFF_LAYER: computes `|original - cloaked| × 50` client-side and downloads as PNG
- Ambient audio toggle (40 Hz binaural drone via Web Audio API, muted by default)
- JSZip batch download for multiple files

---

## Modes (Attack Configurations)

| Mode | Algorithm | Steps | ε (0–255) | Use Case |
|---|---|---|---|---|
| Fast | FGSM | 1 | 2.0 | Quick protection, minimal artifacts |
| Balanced | PGD | 10 | 4.0 | Best tradeoff (recommended) |
| Strong | PGD | 20 | 8.0 | Maximum disruption, slight visible noise |

---

## Verification Utility (`verify_poison.py`)

### Basic Comparison
```bash
python verify_poison.py original.png cloaked.png
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--amplify N` | `50` | Diff amplification multiplier |
| `--output PATH` | `POISON_LAYER_REVEALED.png` | Output diff image path |
| `--compare-clip` | off | Load CLIP and print cosine similarity |
| `--json` | off | Machine-readable JSON output |

### Example with All Flags
```bash
python verify_poison.py photo.png cloaked_photo.png \
    --amplify 100 \
    --output my_diff.png \
    --compare-clip \
    --json
```

### CLIP Cosine Similarity Interpretation
- **> 0.95**: Minimal effect — perturbation barely shifted CLIP features
- **0.80–0.95**: Moderate disruption — partial feature shift
- **< 0.80**: Strong disruption — significant embedding alteration

---

## Performance Notes
- CPU-only. No GPU required.
- First-time model download (~600MB) from Hugging Face; cached after.
- Per-image runtime: 1–5s typical on modern CPU depending on mode and steps.
