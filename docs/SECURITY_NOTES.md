# Security & Expectations

## Threat Model
PixelCloak aims to disrupt training, fine-tuning, and direct querying of vision-based multimodal LLMs by perturbing generic feature space (CLIP/SigLIP). It is designed to act as a **Targeted Feature Collision Attack**, tricking the AI into specifically identifying another user-supplied object, or falling back to raw noise profiles (`assets/default_target.png`). Keep in mind this is an algorithmic deterrent, not cryptographic security.

## Known Weaknesses
- **JPEG Compression / Platform Image Downsizing**: Web platforms (e.g., Discord, OpenAI Chat) heavily downsample images. If they resize the image too drastically, the adversarial pixel layer vanishes. 
  - *Fix*: Activating **EoT Robustness** mathematically predicts this compression dynamically during the process.
- **Tile-based Upscaling Filters (GPT-4o)**: Commercial models cut high-resolution photos into tiles, smoothing out standard uniform noise vectors.
  - *Fix*: PixelCloak computes **mathematical gradients at full native image resolution**. While it is memory-expensive, this is absolutely necessary to bypass the high-frequency blur filters used in GPT-4v/4o.

## Guidance for Users
- Communicate honestly: this is adversarial noise, not cryptography.
- Keep outputs in PNG; avoid any post-processing that re-encodes or compresses.
- Re-run cloaking if you resize or crop after the fact.

## Operational Tips
- Expose headers in responses so UIs can display which mode/ε was used.
- Monitor first-run model download; ensure outbound access to Hugging Face.
