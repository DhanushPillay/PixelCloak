import torch
import torch.nn.functional as F
from torchvision import transforms
import random

def apply_eot(x, use_robustness=False):
    """
    Expectation over Transformation (EoT) logic.
    Simulates JPEG compression (via blur and noise) and random affine transforms 
    so the adversarial perturbation survives chatbot preprocessing.
    """
    if not use_robustness:
        return x
        
    orig_s = x.shape[-1]
    
    # 1. Random Resizing (simulate downscaling/upscaling)
    scale = random.uniform(0.85, 1.15)
    new_s = int(orig_s * scale)
    x_tf = transforms.functional.resize(x, [new_s, new_s], antialias=True)
    
    # Pad or Crop back to original size
    if new_s < orig_s:
        p = orig_s - new_s
        x_tf = transforms.functional.pad(x_tf, [p//2, p//2, p - p//2, p - p//2])
    else:
        x_tf = transforms.functional.center_crop(x_tf, orig_s)
        
    # 2. Additive Gaussian Noise (simulate quantization/compression noise)
    if random.random() < 0.5:
        noise = torch.randn_like(x_tf) * 0.02
        x_tf = torch.clamp(x_tf + noise, 0.0, 1.0)
        
    # 3. Differentiable Blur (simulate JPEG high-frequency loss)
    if random.random() < 0.5:
        x_tf = transforms.functional.gaussian_blur(x_tf, kernel_size=[3, 3])
        
    return x_tf
