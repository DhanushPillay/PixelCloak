"""
PixelCloak Backend — Adversarial Perturbation Engine
Uses CLIP ViT-B/32 as a surrogate model with PGD/FGSM attacks
to disrupt feature-space alignment against diffusion models.

Loss function: negated cosine similarity on L2-normalised CLIP features.
"""

import os
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from PIL import Image

import torch
import torch.nn.functional as F
from torchvision import transforms
from transformers import CLIPModel, CLIPProcessor

import filetype
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = os.environ.get(
    "PIXELCLOAK_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Global model references
# ---------------------------------------------------------------------------

device = torch.device("cpu")
model = None
processor = None

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load CLIP on startup, free memory on shutdown."""
    global model, processor
    print("Loading CLIP model 'openai/clip-vit-base-patch32' on CPU...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    model.eval()
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    print("Model loaded successfully.")
    yield
    # Shutdown: free model memory
    del model, processor
    torch.cuda.empty_cache()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PixelCloak API",
    description="Adversarial Perturbation Engine",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": str(device)
    }

# ---------------------------------------------------------------------------
# PGD / FGSM Attack Engine
# ---------------------------------------------------------------------------

def apply_pgd_attack(image: Image.Image, eps_val: float, steps: int, is_fgsm: bool = False) -> tuple:
    """
    Apply PGD (or FGSM) attack to disrupt CLIP embeddings.

    The core idea: we want to push the adversarial image's CLIP features
    as far away from the original image's features as possible. We do this
    by MAXIMISING the distance (equivalently, MINIMISING cosine similarity).

    Loss = -cosine_similarity(adv_features, orig_features)
    We call loss.backward() and step in the direction of grad.sign()
    which descends this negated similarity — i.e. pushes features apart.

    Returns: (poisoned_image_bytes, processing_time, max_delta_255, mean_delta_255)
    """
    start_time = time.time()

    # 1. Prepare original high-res image tensor
    orig_width, orig_height = image.size
    img_tensor = transforms.ToTensor()(image).unsqueeze(0).to(device)  # [1, 3, H, W], [0, 1]

    # 2. Prepare 224x224 version for CLIP input
    resize_transform = transforms.Resize((224, 224), antialias=True)
    img_224 = resize_transform(img_tensor)

    # CLIP normalisation constants (applied manually so gradients flow to pixels)
    pixel_mean = torch.tensor([0.48145466, 0.4578275, 0.40821073]).view(1, 3, 1, 1).to(device)
    pixel_std = torch.tensor([0.26862954, 0.26130258, 0.27577711]).view(1, 3, 1, 1).to(device)

    def normalize(x):
        return (x - pixel_mean) / pixel_std

    # 3. Extract original (clean) CLIP features — no gradients needed
    with torch.no_grad():
        norm_img_224 = normalize(img_224)
        orig_features = model.get_image_features(norm_img_224)
        orig_features = orig_features / orig_features.norm(p=2, dim=-1, keepdim=True)

    # 4. PGD setup
    eps = eps_val / 255.0
    alpha = (eps * 1.5) / max(steps, 1)  # step size

    # Initialise perturbed image
    if is_fgsm:
        # True FGSM: start from clean image, no random init
        perturbed_224 = img_224.clone().detach()
    else:
        # PGD: random init within epsilon ball
        perturbed_224 = img_224.clone().detach() + torch.empty_like(img_224).uniform_(-eps, eps)
        perturbed_224 = torch.clamp(perturbed_224, 0.0, 1.0)

    # 5. Iterative optimisation loop
    for _ in range(steps):
        # Detach from previous iteration's graph to prevent memory leak
        perturbed_224 = perturbed_224.detach().requires_grad_(True)

        # Forward pass through CLIP
        norm_perturbed = normalize(perturbed_224)
        adv_features = model.get_image_features(norm_perturbed)
        adv_features = adv_features / adv_features.norm(p=2, dim=-1, keepdim=True)

        # Loss: negated cosine similarity
        # We want to MAXIMISE distance, so we MINIMISE (negate) similarity.
        loss = -F.cosine_similarity(adv_features, orig_features).mean()

        model.zero_grad()
        loss.backward()

        # PGD step: move in direction of gradient sign
        with torch.no_grad():
            grad_sign = perturbed_224.grad.sign()
            perturbed_224 = perturbed_224 + alpha * grad_sign

            # Project back into L-inf epsilon ball around clean image
            delta = torch.clamp(perturbed_224 - img_224, min=-eps, max=eps)
            perturbed_224 = torch.clamp(img_224 + delta, min=0.0, max=1.0)

    # 6. Upscale the perturbation delta to original resolution
    final_delta_224 = perturbed_224.detach() - img_224

    if (orig_width, orig_height) != (224, 224):
        upsample = torch.nn.Upsample(
            size=(orig_height, orig_width),
            mode='bilinear',
            align_corners=False
        )
        final_delta_orig = upsample(final_delta_224)
    else:
        final_delta_orig = final_delta_224

    # 7. Apply perturbation to original image
    final_img_tensor = torch.clamp(img_tensor + final_delta_orig, 0.0, 1.0)

    # 8. Compute perturbation statistics (0–255 scale)
    delta_255 = (final_delta_orig.abs() * 255.0).squeeze(0)  # [3, H, W]
    max_delta = float(delta_255.max().item())
    mean_delta = float(delta_255.mean().item())

    # 9. Convert to PIL and serialise as PNG bytes
    final_img_pil = transforms.ToPILImage()(final_img_tensor.squeeze(0).cpu())
    output_buffer = BytesIO()
    final_img_pil.save(output_buffer, format="PNG")

    process_time = time.time() - start_time
    return output_buffer.getvalue(), process_time, max_delta, mean_delta


# ---------------------------------------------------------------------------
# File validation helpers
# ---------------------------------------------------------------------------

def validate_image_bytes(data: bytes) -> bool:
    """Validate file is actually an image using magic bytes, not client headers."""
    kind = filetype.guess(data)
    if kind is None:
        return False
    return kind.mime.startswith("image/")


# ---------------------------------------------------------------------------
# Cloak endpoint
# ---------------------------------------------------------------------------

@app.post("/cloak")
@limiter.limit("10/minute")
async def apply_cloak(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Form("balanced")
):
    # Read raw bytes
    image_data = await file.read()

    # Size check
    if len(image_data) > MAX_FILE_SIZE:
        return JSONResponse(
            status_code=400,
            content={"error": "File size exceeds 10MB limit."}
        )

    # Validate image using magic bytes (not client content-type header)
    if not validate_image_bytes(image_data):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file type. Only image files are allowed."}
        )

    # Try to open with Pillow — rejects corrupt / malicious files
    try:
        img = Image.open(BytesIO(image_data)).convert("RGB")
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Could not decode image. File may be corrupt."}
        )

    # Determine attack parameters from mode
    is_fgsm = False
    if mode == "fast":
        steps = 1
        eps = 2.0
        is_fgsm = True
    elif mode == "strong":
        steps = 20
        eps = 8.0
    else:  # balanced (default)
        mode = "balanced"
        steps = 10
        eps = 4.0

    # Run CPU-bound attack in a thread executor so we don't block the event loop
    loop = asyncio.get_event_loop()
    try:
        poisoned_bytes, p_time, max_delta, mean_delta = await loop.run_in_executor(
            None,
            apply_pgd_attack,
            img, eps, steps, is_fgsm
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error cloaking image: {str(e)}"}
        )

    # Build response with metadata headers
    response = Response(content=poisoned_bytes, media_type="image/png")
    response.headers["X-PixelCloak-Mode"] = mode
    response.headers["X-PixelCloak-Steps"] = str(steps)
    response.headers["X-PixelCloak-Epsilon"] = str(eps)
    response.headers["X-PixelCloak-Time"] = f"{p_time:.2f}s"
    response.headers["X-PixelCloak-MaxDelta"] = f"{max_delta:.2f}"
    response.headers["X-PixelCloak-MeanDelta"] = f"{mean_delta:.2f}"

    # Expose custom headers to browser JS via CORS
    response.headers["Access-Control-Expose-Headers"] = (
        "X-PixelCloak-Mode, X-PixelCloak-Steps, X-PixelCloak-Epsilon, "
        "X-PixelCloak-Time, X-PixelCloak-MaxDelta, X-PixelCloak-MeanDelta"
    )

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
