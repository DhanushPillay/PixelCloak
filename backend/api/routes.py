import asyncio
from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import Response, JSONResponse
from PIL import Image
from io import BytesIO
import filetype

from backend.api.limiter import limiter
from backend.ml.attacks.mi_fgsm import apply_ensemble_mi_fgsm

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
VALID_MODES = {"fast", "balanced", "strong"}
MIN_IMAGE_DIM = 32
MAX_IMAGE_DIM = 8192
PROCESSING_TIMEOUT = 120

def validate_image_bytes(data: bytes) -> bool:
    kind = filetype.guess(data)
    if kind is not None and kind.mime.startswith("image/"):
        return True
    try:
        Image.open(BytesIO(data)).verify()
        return True
    except Exception:
        return False

async def read_upload_with_limit(file: UploadFile, max_size: int) -> tuple[bytes, bool]:
    total = 0
    chunks = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            return b"", True
        chunks.append(chunk)
    return b"".join(chunks), False

@router.post("/cloak")
@limiter.limit("10/minute")
async def apply_cloak(
    request: Request, 
    file: UploadFile = File(...), 
    mode: str = Form("balanced"),
    target_prompt: str = Form(None),
    use_robustness: bool = Form(False)
):
    if mode not in VALID_MODES:
        return JSONResponse(status_code=400, content={"error": f"Invalid mode."})

    image_data, exceeded = await read_upload_with_limit(file, MAX_FILE_SIZE)
    if exceeded:
        return JSONResponse(status_code=400, content={"error": "File size exceeds limit."})

    if not validate_image_bytes(image_data):
        return JSONResponse(status_code=400, content={"error": "Invalid file type."})

    try:
        img = Image.open(BytesIO(image_data)).convert("RGB")
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Could not decode image."})

    w, h = img.size
    if w < MIN_IMAGE_DIM or h < MIN_IMAGE_DIM or w > MAX_IMAGE_DIM or h > MAX_IMAGE_DIM:
        return JSONResponse(status_code=400, content={"error": "Image dimension error."})

    is_fgsm = False
    if mode == "fast":
        steps, eps = 1, 2.0
        is_fgsm = True
    elif mode == "strong":
        steps, eps = 20, 8.0
    else:  
        steps, eps = 10, 4.0

    # Ensure targeted parameters aren't abused on untargeted runs, or clean them up
    prompt_val = target_prompt.strip() if target_prompt else None

    try:
        poisoned_bytes, p_time, max_delta, mean_delta = await asyncio.wait_for(
            asyncio.to_thread(
                apply_ensemble_mi_fgsm, 
                img, eps, steps, is_fgsm, 
                prompt_val, 
                use_robustness, 
                1.0 # decay_momentum
            ),
            timeout=PROCESSING_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"error": "Processing timed out."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Error: {str(e)}"})

    response = Response(content=poisoned_bytes, media_type="image/png")
    response.headers.update({
        "X-PixelCloak-Mode": mode,
        "X-PixelCloak-Steps": str(steps),
        "X-PixelCloak-Epsilon": str(eps),
        "X-PixelCloak-Time": f"{p_time:.2f}s",
        "X-PixelCloak-MaxDelta": f"{max_delta:.2f}",
        "X-PixelCloak-MeanDelta": f"{mean_delta:.2f}",
        "Access-Control-Expose-Headers": "X-PixelCloak-Mode, X-PixelCloak-Steps, X-PixelCloak-Epsilon, X-PixelCloak-Time, X-PixelCloak-MaxDelta, X-PixelCloak-MeanDelta"
    })

    return response
