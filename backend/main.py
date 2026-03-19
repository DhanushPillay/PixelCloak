import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from PIL import Image
import torch
import torch.nn.functional as F
from torchvision import transforms
from transformers import CLIPModel, CLIPProcessor

app = FastAPI(title="PixelCloak API", description="Adversarial Perturbation Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model
device = torch.device("cpu")
model = None
processor = None

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.on_event("startup")
def load_model():
    global model, processor
    print("Loading CLIP model 'openai/clip-vit-base-patch32' on CPU...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    model.eval() # Disable dropout, etc.
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    print("Model loaded successfully.")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": str(device)
    }

def apply_pgd_attack(image: Image.Image, eps_val: float, steps: int) -> tuple:
    """
    Applies PGD attack on the image to disrupt CLIP embeddings.
    Returns: (poisoned_image_bytes, processing_time)
    """
    start_time = time.time()
    
    # 1. Prepare original high-res image
    orig_width, orig_height = image.size
    img_tensor = transforms.ToTensor()(image).unsqueeze(0).to(device) # [1, 3, H, W], [0, 1]
    
    # 2. Prepare 224x224 version for CLIP
    resize_transform = transforms.Resize((224, 224), antialias=True)
    img_224 = resize_transform(img_tensor)
    
    # Note: CLIP normally uses normalization, we'll apply it during the forward pass manually
    # or just rely on the Image Processor for exact values. To keep backprop simple:
    # processor(images=image, return_tensors="pt") does Resizing and Normalizing.
    # We will do normalization manually to allow backprop to the image pixels.
    pixel_mean = torch.tensor([0.48145466, 0.4578275, 0.40821073]).view(1, 3, 1, 1).to(device)
    pixel_std = torch.tensor([0.26862954, 0.26130258, 0.27577711]).view(1, 3, 1, 1).to(device)
    
    def normalize(x):
        return (x - pixel_mean) / pixel_std

    # Get original features
    with torch.no_grad():
        norm_img_224 = normalize(img_224)
        orig_features = model.get_image_features(norm_img_224)
        orig_features = orig_features / orig_features.norm(p=2, dim=-1, keepdim=True)
    
    # PGD Setup
    eps = eps_val / 255.0
    alpha = (eps * 1.5) / max(steps, 1) # Step size
    
    # Initialize perturbed image
    perturbed_224 = img_224.clone().detach() + torch.empty_like(img_224).uniform_(-eps, eps)
    perturbed_224 = torch.clamp(perturbed_224, 0.0, 1.0)
    
    # Needs gradients
    for _ in range(steps):
        perturbed_224.requires_grad = True
        
        # Forward pass
        norm_perturbed = normalize(perturbed_224)
        adv_features = model.get_image_features(norm_perturbed)
        adv_features = adv_features / adv_features.norm(p=2, dim=-1, keepdim=True)
        
        # Loss: minimize cosine similarity -> maximize negative cosine similarity -> or maximize distance
        # We want to push adv_features as far away from orig_features as possible.
        loss = F.mse_loss(adv_features, orig_features)
        
        # Backward pass
        model.zero_grad()
        loss.backward()
        
        # PGD step
        with torch.no_grad():
            grad_sign = perturbed_224.grad.sign()
            perturbed_224 = perturbed_224 + alpha * grad_sign
            
            # Project back to L_inf ball
            delta = torch.clamp(perturbed_224 - img_224, min=-eps, max=eps)
            perturbed_224 = torch.clamp(img_224 + delta, min=0.0, max=1.0)

    # 3. Upscale the perturbation \delta
    final_delta_224 = perturbed_224 - img_224
    
    if (orig_width, orig_height) != (224, 224):
        upsample = torch.nn.Upsample(size=(orig_height, orig_width), mode='bilinear', align_corners=False)
        final_delta_orig = upsample(final_delta_224)
    else:
        final_delta_orig = final_delta_224
        
    # 4. Apply back to original image
    final_img_tensor = torch.clamp(img_tensor + final_delta_orig, 0.0, 1.0)
    
    # 5. Convert to bytes
    final_img_pil = transforms.ToPILImage()(final_img_tensor.squeeze(0).cpu())
    
    output_buffer = BytesIO()
    final_img_pil.save(output_buffer, format="PNG")
    
    process_time = time.time() - start_time
    return output_buffer.getvalue(), process_time

@app.post("/cloak")
async def apply_cloak(
    file: UploadFile = File(...),
    mode: str = Form("balanced")
):
    if not file.content_type.startswith("image/"):
        return JSONResponse(status_code=400, content={"error": "Only images are allowed."})
        
    try:
        image_data = await file.read()
        if len(image_data) > MAX_FILE_SIZE:
             return JSONResponse(status_code=400, content={"error": "File size exceeds 10MB limit."})
        
        img = Image.open(BytesIO(image_data)).convert("RGB")
        
        if mode == "fast":
            steps = 1
            eps = 2.0
        elif mode == "strong":
            steps = 20
            eps = 8.0
        else: # balanced
            steps = 10
            eps = 4.0
            
        poisoned_bytes, p_time = apply_pgd_attack(img, eps_val=eps, steps=steps)
        
        response = Response(content=poisoned_bytes, media_type="image/png")
        # Custom headers to send back metadata
        response.headers["X-PixelCloak-Mode"] = mode
        response.headers["X-PixelCloak-Steps"] = str(steps)
        response.headers["X-PixelCloak-Epsilon"] = str(eps)
        response.headers["X-PixelCloak-Time"] = f"{p_time:.2f}s"
        # Since we use CORS, expose headers
        response.headers["Access-Control-Expose-Headers"] = "X-PixelCloak-Mode, X-PixelCloak-Steps, X-PixelCloak-Epsilon, X-PixelCloak-Time"
        
        return response
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Error cloaking image: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
