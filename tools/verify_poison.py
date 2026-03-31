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


def compare_clip_embeddings(original_path, cloaked_path, target_prompt=None):
    """
    Load CLIP ViT-B/32 and compute cosine similarity.
    If target_prompt is None: returns similarity between original and cloaked image embeddings.
    If target_prompt is given: returns similarity of original to prompt, and cloaked to prompt.
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
    
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
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

        def extract_feats(f):
            if not isinstance(f, torch.Tensor):
                f = getattr(f, "pooler_output", getattr(f, "image_embeds", f))
            return f
            
        feat_orig = extract_feats(feat_orig)
        feat_cloak = extract_feats(feat_cloak)

        # L2-normalise
        feat_orig = feat_orig / feat_orig.norm(p=2, dim=-1, keepdim=True)
        feat_cloak = feat_cloak / feat_cloak.norm(p=2, dim=-1, keepdim=True)
        
        if target_prompt:
            text_inputs = processor(text=[target_prompt], return_tensors="pt", padding=True).to(device)
            feat_text = model.get_text_features(**text_inputs)
            feat_text = extract_feats(feat_text)
            feat_text = feat_text / feat_text.norm(p=2, dim=-1, keepdim=True)
            
            orig_to_text = torch.nn.functional.cosine_similarity(feat_orig, feat_text).item()
            cloak_to_text = torch.nn.functional.cosine_similarity(feat_cloak, feat_text).item()
            
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
                
            return {
                "orig_to_text": round(orig_to_text, 6),
                "cloak_to_text": round(cloak_to_text, 6)
            }
        else:
            cosine_sim = torch.nn.functional.cosine_similarity(feat_orig, feat_cloak).item()

            # Clean up
            del model
            if device.type == "cuda":
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
        "--target-prompt", type=str, default=None,
        help="If provided, also measures similarity between images and this target text prompt."
    )
    parser.add_argument(
        "--compare-all", action="store_true",
        help="Load multiple models (CLIP, SigLIP) to ensure perturbation is ensemble-robust."
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
    clip_sim_result = None
    if args.compare_clip or args.target_prompt:
        clip_sim_result = compare_clip_embeddings(args.original, args.cloaked, args.target_prompt)
        if clip_sim_result is not None:
            if isinstance(clip_sim_result, dict):
                results["clip_similarity_orig_text"] = clip_sim_result["orig_to_text"]
                results["clip_similarity_cloak_text"] = clip_sim_result["cloak_to_text"]
            else:
                results["clip_cosine_similarity"] = clip_sim_result

    if args.compare_all:
        import torch
        from transformers import CLIPModel, CLIPProcessor, AutoModel, AutoProcessor
        
        print("\nLoading models for Ensemble Robustness Check...")
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        
        models_to_test = [
            ("CLIP ViT-B/32", "openai/clip-vit-base-patch32", CLIPModel, CLIPProcessor),
            ("CLIP ViT-L/14", "openai/clip-vit-large-patch14", CLIPModel, CLIPProcessor),
            ("SigLIP Base", "google/siglip-base-patch16-224", AutoModel, AutoProcessor)
        ]
        
        results["ensemble_similarities"] = {}
        for name, repo, MClass, PClass in models_to_test:
            try:
                print(f"  Testing against {name}...")
                model = MClass.from_pretrained(repo).to(device).eval()
                processor = PClass.from_pretrained(repo)
                
                img_orig = Image.open(args.original).convert("RGB")
                img_cloak = Image.open(args.cloaked).convert("RGB")
                
                inputs_orig = processor(images=img_orig, return_tensors="pt").to(device)
                inputs_cloak = processor(images=img_cloak, return_tensors="pt").to(device)
                
                with torch.no_grad():
                    if 'clip' in repo.lower():
                        feat_orig = model.get_image_features(**inputs_orig)
                        feat_cloak = model.get_image_features(**inputs_cloak)
                    else:
                        feat_orig = model.get_image_features(**inputs_orig)
                        feat_cloak = model.get_image_features(**inputs_cloak)
                        
                    def extract_feats(f):
                        return getattr(f, "pooler_output", getattr(f, "image_embeds", getattr(f, "last_hidden_state", f)))

                    feat_orig = extract_feats(feat_orig)
                    feat_cloak = extract_feats(feat_cloak)
                    
                    if isinstance(feat_orig, torch.Tensor) and feat_orig.ndim == 3:
                         feat_orig = feat_orig[:, 0, :]
                         feat_cloak = feat_cloak[:, 0, :]
                         
                    feat_orig = feat_orig / feat_orig.norm(p=2, dim=-1, keepdim=True)
                    feat_cloak = feat_cloak / feat_cloak.norm(p=2, dim=-1, keepdim=True)
                    sim = torch.nn.functional.cosine_similarity(feat_orig, feat_cloak).item()
                    results["ensemble_similarities"][name] = round(sim, 4)
            except Exception as e:
                print(f"  Could not test {name}: {e}")
                
            # Clear memory immediately
            try:
                del model, processor, inputs_orig, inputs_cloak, feat_orig, feat_cloak
                if device == "cuda": torch.cuda.empty_cache()
            except:
                pass

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

        if clip_sim_result is not None:
            if isinstance(clip_sim_result, dict):
                print(f"\n🔬 CLIP Text-Targeted Similarity (Target: '{args.target_prompt}')")
                print(f"   Original -> Text: {clip_sim_result['orig_to_text']:.6f}")
                print(f"   Cloaked  -> Text: {clip_sim_result['cloak_to_text']:.6f}")
                diff = clip_sim_result['cloak_to_text'] - clip_sim_result['orig_to_text']
                if diff > 0.05:
                    print(f"   ✅ Targeted attack successful (+{diff:.4f} similarity to target)")
                else:
                    print(f"   ⚠  Targeted attack had minimal impact.")
            else:
                print(f"\n🔬 CLIP Cosine Similarity: {clip_sim_result:.6f}")
                if clip_sim_result > 0.95:
                    print("   ⚠  High similarity — perturbation had minimal effect on CLIP features.")
                elif clip_sim_result > 0.80:
                    print("   ✓  Moderate disruption — CLIP features partially shifted.")
                else:
                    print("   ✅ Strong disruption — CLIP features heavily distorted.")

            if "ensemble_similarities" in results:
                print("\n🔬 Ensemble Robustness Check (Original vs Cloaked)")
                for name, sim in results["ensemble_similarities"].items():
                    print(f"  {name}: {sim:.4f} " + ("✅ SUCCESS" if sim < 0.8 else "⚠️ MAYBE WEAK"))
                    
if __name__ == "__main__":
    main()
