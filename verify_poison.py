import sys
from PIL import Image, ImageChops
import numpy as np

def verify_images(original_path, cloaked_path):
    print(f"Loading '{original_path}' and '{cloaked_path}'...")
    try:
        # Load both images
        img_orig = Image.open(original_path).convert("RGB")
        img_cloak = Image.open(cloaked_path).convert("RGB")
        
        # Check if dimensions match
        if img_orig.size != img_cloak.size:
            print("Error: Image dimensions do not match. Are you sure these are the same image?")
            return

        # Convert to numpy arrays to do mathematical comparison
        arr_orig = np.array(img_orig, dtype=np.int16)
        arr_cloak = np.array(img_cloak, dtype=np.int16)
        
        # Calculate the exact mathematical difference
        diff_array = np.abs(arr_cloak - arr_orig)
        
        # Check if they are actually identical
        if np.sum(diff_array) == 0:
            print("\n❌ RESULT: The images are mathematically IDENTICAL.")
            print("The cloaking process failed or you passed the same image twice.")
            return
            
        # Calculate statistics
        max_diff = np.max(diff_array)
        avg_diff = np.mean(diff_array)
        pixels_changed = np.sum(diff_array > 0)
        total_pixels = diff_array.size // 3 # Divide by 3 for RGB channels
        
        print("\n✅ RESULT: The images are mathematically DIFFERENT.")
        print(f"-> Maximum color shift on a single pixel: {max_diff} (out of 255)")
        print(f"-> Average color shift per pixel: {avg_diff:.2f}")
        print(f"-> Pixels injected with poison: {pixels_changed:,} / {total_pixels:,} ({(pixels_changed/total_pixels)*100:.1f}%)")
        
        # Create a visual representation of the poison layer itself
        # We multiply by 50 to make the invisible noise visible to the human eye
        print("\nExtracting the invisible poison layer...")
        amplified_diff = np.clip(diff_array * 50, 0, 255).astype(np.uint8)
        diff_img = Image.fromarray(amplified_diff)
        diff_img.save("POISON_LAYER_REVEALED.png")
        print("-> Saved 'POISON_LAYER_REVEALED.png'. Open this file to literally see the mathematical noise.")

    except Exception as e:
        print(f"Error analyzing images: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python verify_poison.py <path_to_original_image> <path_to_cloaked_image>")
        print("Example: python verify_poison.py my_selfie.jpg cloaked_my_selfie.png")
    else:
        verify_images(sys.argv[1], sys.argv[2])
