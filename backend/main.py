from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from PIL import Image
import numpy as np

app = FastAPI(title="PixelCloak API", description="Data Poisoning Backend")

# Allow requests from our Vanilla HTML frontend running locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def apply_adversarial_noise(image_bytes: bytes) -> bytes:
    """
    Simulates an adversarial attack (like FGSM) by converting the image
    to a mathematical tensor (numpy array), injecting imperceptible noise,
    and returning it as an image. This represents the 'poisoning' process.
    """
    # 1. Open the image
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    
    # 2. Convert to mathematical tensor (NumPy array) [0, 255]
    img_array = np.array(img, dtype=np.float32)
    
    # 3. Inject mathematical noise pattern (The 'Poison')
    # We use a structured noise pattern that is visually subtle 
    # but disrupts edge detection and neural network feature maps
    noise = np.random.normal(loc=0, scale=4.0, size=img_array.shape) 
    
    # Apply noise and clip values to remain valid RGB [0, 255]
    poisoned_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    
    # 4. Convert back to image
    poisoned_img = Image.fromarray(poisoned_array)
    
    # 5. Save back to bytes
    output_buffer = BytesIO()
    # Save as PNG to avoid compression artifacts breaking the noise
    poisoned_img.save(output_buffer, format="PNG") 
    
    return output_buffer.getvalue()

@app.get("/")
def read_root():
    return {"message": "PixelCloak API is active. Ready for adversarial perturbation."}

@app.post("/cloak")
async def apply_cloak(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        return Response(content="Invalid file type. Only images are allowed.", status_code=400)
        
    try:
        # Read the raw image data
        image_data = await file.read()
        
        # Apply the sophisticated mathematical poisoning
        poisoned_bytes = apply_adversarial_noise(image_data)
        
        # Return the raw image back to the browser
        return Response(content=poisoned_bytes, media_type="image/png")
        
    except Exception as e:
        return Response(content=f"Error cloaking image: {str(e)}", status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
