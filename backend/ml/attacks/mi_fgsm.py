import time
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
from io import BytesIO

from backend.ml.models import get_ensemble, get_lpips, get_device
from backend.ml.attacks.eot import apply_eot

def extract_features(model_dict, x_norm, device):
    """Safely extracts pooled visual features depending on architecture."""
    model = model_dict["model"]
    m_type = model_dict["type"]
    
    # Needs to match model dtype if using float16
    dtype = next(model.parameters()).dtype
    x_norm = x_norm.to(dtype)

    if m_type == "clip":
        feats = model.get_image_features(pixel_values=x_norm)
    elif m_type == "siglip":
        feats = model.get_image_features(pixel_values=x_norm)
    else:
        feats = model(pixel_values=x_norm)
        
    if hasattr(feats, "pooler_output"):
        feats = feats.pooler_output
    elif hasattr(feats, "image_embeds"):
        feats = feats.image_embeds
    elif hasattr(feats, "last_hidden_state"):
        feats = feats.last_hidden_state[:, 0, :]
    elif isinstance(feats, tuple):
        feats = feats[0]

    return feats / feats.norm(p=2, dim=-1, keepdim=True)

def apply_ensemble_mi_fgsm(image: Image.Image, eps_val: float, steps: int, 
                           is_fgsm: bool = False, target_prompt: str = None, 
                           use_robustness: bool = False, decay_momentum: float = 1.0,
                           target_image: Image.Image = None) -> tuple:
    """
    Applies Momentum-Iterative FGSM across an ensemble of vision encoders.
    """
    start_time = time.time()
    device = get_device()
    ensemble = get_ensemble()
    lpips_model = get_lpips()

    if not ensemble:
        raise ValueError("No models loaded in the ensemble.")

    # 1. Prepare original high-res image tensor
    orig_width, orig_height = image.size
    img_tensor = transforms.ToTensor()(image).unsqueeze(0).to(device)

    # 2. Extract targets for each model
    targets_per_model = []
    
    # We'll optimize the full-resolution image instead of a 224x224 thumbnail.
    # Commercial AI like GPT-4o processes high-resolution tile grids; if we
    # upscale a tiny 224x224 noise patch, it becomes soft, low-frequency blur
    # which their visual filters easily ignore. We MUST compute gradients at native res.
    model_resize = transforms.Resize((224, 224), antialias=True)

    # Perceptual edge mask for dynamic epsilon at NATIVE resolution
    gray = img_tensor.mean(dim=1, keepdim=True)
    sobel_x = torch.tensor([[-1., 0., 1.], [-2., 0., 2.], [-1., 0., 1.]], device=device).view(1,1,3,3)
    sobel_y = torch.tensor([[-1., -2., -1.], [0., 0., 0.], [1., 2., 1.]], device=device).view(1,1,3,3)
    edge_x = F.conv2d(gray, sobel_x, padding=1)
    edge_y = F.conv2d(gray, sobel_y, padding=1)
    edges = torch.sqrt(edge_x**2 + edge_y**2 + 1e-8)
    # Pad back to original size due to conv2d reducing dimension by 2
    edges = F.pad(edges, (1, 1, 1, 1), mode='replicate')
    edges_norm = edges / (edges.max() + 1e-8)
    perceptual_mask = torch.clamp(edges_norm + 0.3, max=1.0)

    # Pre-calculate target features for the ensemble (this is still evaluated at 224x224)
    img_base_224 = model_resize(img_tensor)
    with torch.no_grad():
        for m_dict in ensemble:
            model = m_dict["model"]
            proc = m_dict["processor"]
            m_type = m_dict["type"]
            dtype = next(model.parameters()).dtype

            if target_image:
                # Targeted image attack (Feature Collision)
                target_tensor = transforms.ToTensor()(target_image).unsqueeze(0).to(device)
                target_224 = model_resize(target_tensor)
                
                mean = torch.tensor(m_dict["mean"]).view(1, 3, 1, 1).to(device)
                std = torch.tensor(m_dict["std"]).view(1, 3, 1, 1).to(device)
                norm_target_224 = (target_224 - mean) / std
                
                t_feats = extract_features(m_dict, norm_target_224, device)
                targets_per_model.append(t_feats)
            elif target_prompt and target_prompt.strip() and m_type == "clip":
                # Targeted text attack (only standard CLIP supported for direct text inject right now)
                inputs = proc(text=[target_prompt.strip()], return_tensors="pt", padding=True).to(device)
                t_feats = model.get_text_features(**inputs)
                t_feats = t_feats / t_feats.norm(p=2, dim=-1, keepdim=True)
                targets_per_model.append(t_feats)
            else:
                # Untargeted: push away from original features
                mean = torch.tensor(m_dict["mean"]).view(1, 3, 1, 1).to(device)
                std = torch.tensor(m_dict["std"]).view(1, 3, 1, 1).to(device)
                norm_img_224 = (img_base_224 - mean) / std
                
                t_feats = extract_features(m_dict, norm_img_224, device)
                targets_per_model.append(t_feats)

    # 3. MI-FGSM setup
    eps_base = eps_val / 255.0
    dynamic_eps = eps_base * perceptual_mask
    alpha = (dynamic_eps * 1.5) / max(steps, 1)

    if is_fgsm:
        perturbed_tensor = img_tensor.clone().detach()
    else:
        noise = torch.empty_like(img_tensor).uniform_(-1, 1) * dynamic_eps
        perturbed_tensor = torch.clamp(img_tensor.clone().detach() + noise, 0.0, 1.0)

    momentum_g = torch.zeros_like(img_tensor)

    # 4. Iterative Optimization
    for step in range(steps):
        perturbed_tensor = perturbed_tensor.detach().requires_grad_(True)
        
        # Apply EoT at full resolution, then downscale for the models
        adv_input = apply_eot(perturbed_tensor, use_robustness)
        adv_input_224 = model_resize(adv_input)
        total_obj = 0.0

        for i, m_dict in enumerate(ensemble):
            mean = torch.tensor(m_dict["mean"]).view(1, 3, 1, 1).to(device)
            std = torch.tensor(m_dict["std"]).view(1, 3, 1, 1).to(device)
            norm_perturbed = (adv_input_224 - mean) / std

            adv_features = extract_features(m_dict, norm_perturbed, device)
            t_feats = targets_per_model[i]

            if target_image:
                # Maximize cosine similarity to targeted image (Feature Collision)
                total_obj += F.cosine_similarity(adv_features, t_feats).mean()
            elif target_prompt and target_prompt.strip() and m_dict["type"] == "clip":
                # Maximize cosine similarity to targeted text
                total_obj += F.cosine_similarity(adv_features, t_feats).mean()
            else:
                # Maximize distance from original features
                total_obj += -F.cosine_similarity(adv_features, t_feats).mean()

        # Average objective across ensemble
        total_obj = total_obj / len(ensemble)

        # LPIPS Regularization to maintain visual quality
        if lpips_model is not None:
            adv_lpips = adv_input_224 * 2.0 - 1.0
            orig_lpips = img_base_224 * 2.0 - 1.0
            # Float32 required for LPIPS usually
            perceptual_dist = lpips_model(adv_lpips.to(torch.float32), orig_lpips.to(torch.float32)).mean()
            total_obj = total_obj - 0.5 * perceptual_dist

        # Zero gradients
        for m_dict in ensemble:
            m_dict["model"].zero_grad()
        if lpips_model:
            lpips_model.zero_grad()

        # Backward pass
        total_obj.backward()

        # Update with Momentum (MI-FGSM)
        with torch.no_grad():
            grad = perturbed_tensor.grad
            # L1 norm standardization for momentum
            grad_l1_norm = torch.norm(grad, p=1, dim=[1, 2, 3], keepdim=True)
            grad_normalized = grad / (grad_l1_norm + 1e-8)
            
            momentum_g = decay_momentum * momentum_g + grad_normalized
            
            # Step in direction of momentum
            perturbed_tensor = perturbed_tensor + alpha * momentum_g.sign()

            # Project to epsilon ball
            delta = torch.clamp(perturbed_tensor - img_tensor, min=-dynamic_eps, max=dynamic_eps)
            perturbed_tensor = torch.clamp(img_tensor + delta, min=0.0, max=1.0)

    # 5. Extract the final native-resolution delta
    final_delta_orig = perturbed_tensor.detach() - img_tensor

    # 6. Apply to original image
    final_img_tensor = torch.clamp(img_tensor + final_delta_orig, 0.0, 1.0)

    # 7. Stats
    delta_255 = (final_delta_orig.abs() * 255.0).squeeze(0)
    max_delta = float(delta_255.max().item())
    mean_delta = float(delta_255.mean().item())

    # 8. Encode bytes
    final_img_pil = transforms.ToPILImage()(final_img_tensor.squeeze(0).cpu().to(torch.float32))
    output_buffer = BytesIO()
    final_img_pil.save(output_buffer, format="PNG")

    process_time = time.time() - start_time
    return output_buffer.getvalue(), process_time, max_delta, mean_delta
