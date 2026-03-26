"""
PixelCloak — Poison Layer Verification Utility

Compares an original image to its cloaked counterpart, computing
pixel-level statistics and optionally measuring CLIP embedding
disruption via cosine similarity.

Usage:
    python verify_poison.py original.png cloaked.png
    python verify_poison.py original.png cloaked.png --amplify 100 --output diff.png
    python verify_poison.py original.png cloaked.png --compare-clip --json
"""

import argparse
import json
import sys

import numpy as np
from PIL import Image


def verify_images(original_path, cloaked_path, amplify=50, output_path="POISON_LAYER_REVEALED.png"):
    """
    Compare two images pixel-by-pixel and produce statistics + amplified diff.
    Returns a dict of results, or None on error.
    """
    try:
        img_orig = Image.open(original_path).convert("RGB")
        img_cloak = Image.open(cloaked_path).convert("RGB")
    except Exception as e:
        print(f"Error loading images: {e}", file=sys.stderr)
        return None

    if img_orig.size != img_cloak.size:
        print("Error: Image dimensions do not match.", file=sys.stderr)
        return None

    arr_orig = np.array(img_orig, dtype=np.int16)
    arr_cloak = np.array(img_cloak, dtype=np.int16)

    diff_array = np.abs(arr_cloak - arr_orig)

    if np.sum(diff_array) == 0:
        return {
            "status": "identical",
            "message": "Images are mathematically IDENTICAL. Cloaking may have failed.",
            "max_diff": 0,
            "avg_diff": 0.0,
            "pixels_changed": 0,
            "total_pixels": int(diff_array.size // 3),
            "percent_changed": 0.0
        }

    max_diff = int(np.max(diff_array))
    avg_diff = float(np.mean(diff_array))
    pixels_changed = int(np.sum(np.any(diff_array > 0, axis=-1)))
    total_pixels = int(arr_orig.shape[0] * arr_orig.shape[1])
    percent_changed = (pixels_changed / total_pixels) * 100

    # Create amplified diff image
    amplified_diff = np.clip(diff_array * amplify, 0, 255).astype(np.uint8)
    diff_img = Image.fromarray(amplified_diff)
    diff_img.save(output_path)

    return {
        "status": "different",
        "message": "Images are mathematically DIFFERENT. Perturbation detected.",
        "max_diff": max_diff,
        "avg_diff": round(avg_diff, 4),
        "pixels_changed": pixels_changed,
        "total_pixels": total_pixels,
        "percent_changed": round(percent_changed, 2),
        "amplify_factor": amplify,
        "diff_image_path": output_path
    }


def compare_clip_embeddings(original_path, cloaked_path):
    """
    Load CLIP ViT-B/32 and compute cosine similarity between the
    original and cloaked image embeddings. This is the single most
    useful metric for quantifying how much the attack disrupted
    CLIP's understanding of the image.

    Returns cosine similarity as a float (lower = more disrupted).
    """
    try:
        import torch
        from torchvision import transforms
        from transformers import CLIPModel, CLIPProcessor
    except ImportError:
        print(
            "Error: --compare-clip requires torch, torchvision, and transformers.\n"
            "Install with: pip install torch torchvision transformers",
            file=sys.stderr
        )
        return None

    print("Loading CLIP model for embedding comparison...")
    device = torch.device("cpu")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    model.eval()
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    img_orig = Image.open(original_path).convert("RGB")
    img_cloak = Image.open(cloaked_path).convert("RGB")

    with torch.no_grad():
        inputs_orig = processor(images=img_orig, return_tensors="pt").to(device)
        inputs_cloak = processor(images=img_cloak, return_tensors="pt").to(device)

        feat_orig = model.get_image_features(**inputs_orig)
        feat_cloak = model.get_image_features(**inputs_cloak)

        # L2-normalise
        feat_orig = feat_orig / feat_orig.norm(p=2, dim=-1, keepdim=True)
        feat_cloak = feat_cloak / feat_cloak.norm(p=2, dim=-1, keepdim=True)

        cosine_sim = torch.nn.functional.cosine_similarity(feat_orig, feat_cloak).item()

    # Clean up
    del model
    torch.cuda.empty_cache()

    return round(cosine_sim, 6)


def main():
    parser = argparse.ArgumentParser(
        description="PixelCloak — Verify adversarial perturbation between original and cloaked images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python verify_poison.py photo.png cloaked_photo.png\n"
               "  python verify_poison.py photo.png cloaked_photo.png --amplify 100 --output diff.png\n"
               "  python verify_poison.py photo.png cloaked_photo.png --compare-clip --json\n"
    )

    parser.add_argument("original", help="Path to the original (clean) image")
    parser.add_argument("cloaked", help="Path to the cloaked (perturbed) image")
    parser.add_argument(
        "--amplify", type=int, default=50,
        help="Amplification multiplier for the diff image (default: 50)"
    )
    parser.add_argument(
        "--output", type=str, default="POISON_LAYER_REVEALED.png",
        help="Output path for the amplified diff PNG (default: POISON_LAYER_REVEALED.png)"
    )
    parser.add_argument(
        "--compare-clip", action="store_true",
        help="Load CLIP ViT-B/32 and print cosine similarity between original and cloaked embeddings"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print results as machine-readable JSON"
    )

    args = parser.parse_args()

    # Run pixel-level comparison
    print(f"Loading '{args.original}' and '{args.cloaked}'...")
    results = verify_images(args.original, args.cloaked, amplify=args.amplify, output_path=args.output)

    if results is None:
        sys.exit(1)

    # Optional CLIP comparison
    clip_sim = None
    if args.compare_clip:
        clip_sim = compare_clip_embeddings(args.original, args.cloaked)
        if clip_sim is not None:
            results["clip_cosine_similarity"] = clip_sim

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if results["status"] == "identical":
            print(f"\n❌ RESULT: {results['message']}")
        else:
            print(f"\n✅ RESULT: {results['message']}")
            print(f"-> Maximum color shift on a single pixel: {results['max_diff']} (out of 255)")
            print(f"-> Average color shift per pixel: {results['avg_diff']:.2f}")
            print(f"-> Pixels injected with poison: {results['pixels_changed']:,} / {results['total_pixels']:,} ({results['percent_changed']:.1f}%)")
            print(f"\nExtracted poison layer (amplified {args.amplify}×):")
            print(f"-> Saved '{args.output}'")

        if clip_sim is not None:
            print(f"\n🔬 CLIP Cosine Similarity: {clip_sim:.6f}")
            if clip_sim > 0.95:
                print("   ⚠  High similarity — perturbation had minimal effect on CLIP features.")
            elif clip_sim > 0.80:
                print("   ✓  Moderate disruption — CLIP features partially shifted.")
            else:
                print("   ✓✓ Strong disruption — CLIP features significantly altered.")


if __name__ == "__main__":
    main()
