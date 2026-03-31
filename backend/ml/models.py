import torch
from transformers import CLIPModel, CLIPProcessor, AutoModel, AutoProcessor
import lpips

# Device selection
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

# Global registries
ensemble_models = []
lpips_model = None

def load_models():
    """Loads a diverse ensemble of vision encoders and LPIPS for perceptual regularization."""
    global ensemble_models, lpips_model
    
    print(f"Loading Models onto {device} (using float16 if CUDA)...")
    dtype = torch.float16 if device.type == "cuda" else torch.float32

    # 1. CLIP ViT-B/32 (Baseline)
    print("Loading openai/clip-vit-base-patch32...")
    clip_base = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", torch_dtype=dtype).to(device)
    clip_base.eval()
    clip_base_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    ensemble_models.append({
        "type": "clip",
        "model": clip_base,
        "processor": clip_base_proc,
        "size": 224,
        "mean": [0.48145466, 0.4578275, 0.40821073],
        "std": [0.26862954, 0.26130258, 0.27577711]
    })
    
    # 2. CLIP ViT-L/14 (Higher resolution, deeper)
    print("Loading openai/clip-vit-large-patch14...")
    clip_large = CLIPModel.from_pretrained("openai/clip-vit-large-patch14", torch_dtype=dtype).to(device)
    clip_large.eval()
    clip_large_proc = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
    ensemble_models.append({
        "type": "clip",
        "model": clip_large,
        "processor": clip_large_proc,
        "size": 224, 
        "mean": [0.48145466, 0.4578275, 0.40821073],
        "std": [0.26862954, 0.26130258, 0.27577711]
    })
    
    # 3. SigLIP Base (Different training objective, highly robust)
    print("Loading google/siglip-base-patch16-224...")
    try:
        siglip = AutoModel.from_pretrained("google/siglip-base-patch16-224", torch_dtype=dtype).to(device)
        siglip.eval()
        siglip_proc = AutoProcessor.from_pretrained("google/siglip-base-patch16-224")
        ensemble_models.append({
            "type": "siglip",
            "model": siglip,
            "processor": siglip_proc,
            "size": 224,
            "mean": [0.5, 0.5, 0.5], # SigLIP uses 0.5 mean/std for [-1, 1] scaling usually
            "std": [0.5, 0.5, 0.5]
        })
    except Exception as e:
        print(f"Failed to load SigLIP (maybe transformers is outdated), skipping: {e}")

    # LPIPS for perceptual constraint
    print("Loading LPIPS model...")
    lpips_model = lpips.LPIPS(net='alex').to(device)
    if device.type == "cuda":
        # Keep lpips in float32 usually for stability, but we can do it if needed
        pass
    lpips_model.eval()

    print("All models loaded successfully.")

def unload_models():
    """Frees up VRAM."""
    global ensemble_models, lpips_model
    ensemble_models.clear()
    lpips_model = None
    if device.type == "cuda":
        torch.cuda.empty_cache()
    elif device.type == "mps":
        torch.mps.empty_cache()

def get_ensemble():
    return ensemble_models

def get_lpips():
    return lpips_model

def get_device():
    return device
