# Security & Expectations

## Threat Model
PixelCloak aims to disrupt training/fine-tuning of diffusion-style models by perturbing CLIP feature space. It is a deterrent for naive scraping, not a guarantee against targeted removal.

## Known Weaknesses
- JPEG compression or aggressive downscaling often destroys adversarial signal.
- Diffusion-based "purification" (img2img with low denoise strength) can neutralize perturbations.
- Stronger ε values increase visibility; keep exports as PNG.

## Guidance for Users
- Communicate honestly: this is adversarial noise, not cryptography.
- Keep outputs in PNG; avoid any post-processing that re-encodes or compresses.
- Re-run cloaking if you resize or crop after the fact.

## Operational Tips
- Expose headers in responses so UIs can display which mode/ε was used.
- Monitor first-run model download; ensure outbound access to Hugging Face.
