"""
PixelCloak Backend — Adversarial Perturbation Engine
Uses Ensemble Models with Momentum Iterative PGD (MI-FGSM) 
and Expectation over Transformation (EoT) for robust misclassification.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from backend.api.limiter import limiter
from backend.api.routes import router as cloak_router
from backend.ml.models import load_models, unload_models, get_device, get_ensemble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = os.environ.get(
    "PIXELCLOAK_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

ALLOWED_ORIGIN_REGEX = os.environ.get(
    "PIXELCLOAK_ALLOWED_ORIGIN_REGEX",
    r"https?://(localhost|127\.0\.0\.1)(:\d+)?|file://.*"
)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load Vision Encoder Ensemble on startup, free memory on shutdown."""
    load_models()
    yield
    unload_models()

# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PixelCloak API",
    description="Ensemble Adversarial Perturbation Engine",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cloak_router)

@app.get("/health")
def health_check():
    ensemble = get_ensemble()
    return {
        "status": "healthy",
        "models_loaded": len(ensemble),
        "device": str(get_device())
    }

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend_vanilla")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
