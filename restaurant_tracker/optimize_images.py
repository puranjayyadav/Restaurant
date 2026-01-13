"""
Batch resize and convert images to WebP format before uploading to Supabase.
This reduces bandwidth costs significantly.

Optimizations:
- Max width: 800px (mobile screens don't need 4K)
- Format: WebP (smaller than JPG)
- Quality: 85% (good balance between quality and size)
"""
import os
import sys
from pathlib import Path
from PIL import Image
import argparse

# Force unbuffered output
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

print("=" * 60, flush=True)
print("IMAGE OPTIMIZER - Resize & Convert to WebP", flush=True)
print("=" * 60, flush=True)


def optimize_image(input_path: str, output_path: str = None, max_width: int = 800, 
                  quality: int = 85) -> tuple:
    """
    Optimize a single image: resize to max_width and convert to WebP.
    Returns (success: bool, original_size: int, optimized_size: int, saved_bytes: int)
    """
    try:
        # Open image
        with Image.open(input_path) as img:
            original_size = os.path.getsize(input_path)
            
            # Convert RGBA to RGB if necessary (WebP doesn't support RGBA well)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate new dimensions
            width, height = img.size
            if width > max_width:
                # Maintain aspect ratio
                ratio = max_width / width
                new_width = max_width
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Determine output path
            if output_path is None:
                # Replace extension with .webp
                base_path = os.path.splitext(input_path)[0]
                output_path = f"{base_path}.webp"
            
            # Save as WebP
            img.save(output_path, 'WEBP', quality=quality, method=6)
            
            optimized_size = os.path.getsize(output_path)
            saved_bytes = original_size - optimized_size
            saved_percent = (saved_bytes / original_size * 100) if original_size > 0 else 0
            
            return True, original_size, optimized_size, saved_bytes, saved_percent
            
    except Exception as e:
        print(f"  ⚠️  Error optimizing {os.path.basename(input_path)}: {e}", flush=True)
        return False, 0, 0, 0, 0


def optimize_directory(directory: str, output_dir: str = None, max_width: int = 800,
                       quality: int = 85, replace_original: bool = False) -> dict:
    """
    Optimize all images in a directory.
    Returns statistics dictionary.
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        print(f"❌ Directory not found: {directory}", flush=True)
        return {}
    
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(directory_path.rglob(f'*{ext}'))
        image_files.extend(directory_path.rglob(f'*{ext.upper()}'))
    
    if not image_files:
        print(f"⚠️  No images found in {directory}", flush=True)
        return {}
    
    print(f"📂 Found {len(image_files)} images to optimize", flush=True)
    print()
    
    # Statistics
    stats = {
        'total': len(image_files),
        'success': 0,
        'failed': 0,
        'original_total_size': 0,
        'optimized_total_size': 0,
        'total_saved': 0
    }
    
    # Process each image
    for idx, image_path in enumerate(image_files, 1):
        try:
            # Skip if already WebP and we're not replacing
            if image_path.suffix.lower() == '.webp' and not replace_original:
                print(f"[{idx}/{len(image_files)}] ⏭️  Already WebP: {image_path.name}", flush=True)
                continue
            
            # Determine output path
            if output_dir:
                # Maintain directory structure
                relative_path = image_path.relative_to(directory_path)
                output_path = Path(output_dir) / relative_path.with_suffix('.webp')
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path_str = str(output_path)
            elif replace_original:
                # Replace original with WebP
                output_path_str = str(image_path.with_suffix('.webp'))
            else:
                # Save next to original
                output_path_str = str(image_path.with_suffix('.webp'))
            
            # Skip if output already exists and is newer
            if os.path.exists(output_path_str) and not replace_original:
                if os.path.getmtime(output_path_str) >= os.path.getmtime(image_path):
                    print(f"[{idx}/{len(image_files)}] ⏭️  Already optimized: {image_path.name}", flush=True)
                    continue
            
            print(f"[{idx}/{len(image_files)}] 🔧 Optimizing: {image_path.name}...", end=" ", flush=True)
            
            success, orig_size, opt_size, saved, saved_pct = optimize_image(
                str(image_path), output_path_str, max_width, quality
            )
            
            if success:
                stats['success'] += 1
                stats['original_total_size'] += orig_size
                stats['optimized_total_size'] += opt_size
                stats['total_saved'] += saved
                
                orig_mb = orig_size / (1024 * 1024)
                opt_mb = opt_size / (1024 * 1024)
                saved_mb = saved / (1024 * 1024)
                
                print(f"✅ {orig_mb:.2f}MB → {opt_mb:.2f}MB ({saved_pct:.1f}% saved, -{saved_mb:.2f}MB)", flush=True)
                
                # Remove original if replacing
                if replace_original and image_path.suffix.lower() != '.webp':
                    try:
                        image_path.unlink()
                    except:
                        pass
            else:
                stats['failed'] += 1
                print(f"❌ Failed", flush=True)
                
        except Exception as e:
            stats['failed'] += 1
            print(f"❌ Error: {e}", flush=True)
    
    return stats


def optimize_restaurant_images(restaurant_images_dir: str = "restaurant_images",
                              output_dir: str = None, max_width: int = 800,
                              quality: int = 85, replace_original: bool = False):
    """Optimize all images in restaurant_images directory"""
    
    print(f"📁 Processing directory: {restaurant_images_dir}", flush=True)
    print(f"   Max width: {max_width}px", flush=True)
    print(f"   Quality: {quality}%", flush=True)
    print(f"   Format: WebP", flush=True)
    print()
    
    stats = optimize_directory(
        restaurant_images_dir,
        output_dir=output_dir,
        max_width=max_width,
        quality=quality,
        replace_original=replace_original
    )
    
    if not stats:
        return
    
    # Print summary
    print()
    print("=" * 60, flush=True)
    print("OPTIMIZATION SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"✅ Successfully optimized: {stats['success']}", flush=True)
    print(f"❌ Failed: {stats['failed']}", flush=True)
    print(f"📊 Total images: {stats['total']}", flush=True)
    print()
    
    if stats['success'] > 0:
        orig_total_mb = stats['original_total_size'] / (1024 * 1024)
        opt_total_mb = stats['optimized_total_size'] / (1024 * 1024)
        saved_total_mb = stats['total_saved'] / (1024 * 1024)
        saved_percent = (stats['total_saved'] / stats['original_total_size'] * 100) if stats['original_total_size'] > 0 else 0
        
        print(f"📦 Original total size: {orig_total_mb:.2f} MB", flush=True)
        print(f"📦 Optimized total size: {opt_total_mb:.2f} MB", flush=True)
        print(f"💾 Total saved: {saved_total_mb:.2f} MB ({saved_percent:.1f}%)", flush=True)
        print()
        print(f"💰 Bandwidth savings: ~{saved_total_mb:.2f} MB per 1,000 users", flush=True)
        print(f"   (Supabase Free Tier: 2GB/month)", flush=True)
    
    print("=" * 60, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Optimize images by resizing and converting to WebP format"
    )
    parser.add_argument("--input-dir", default="restaurant_images",
                       help="Input directory containing images")
    parser.add_argument("--output-dir", default=None,
                       help="Output directory (if not set, saves next to originals)")
    parser.add_argument("--max-width", type=int, default=800,
                       help="Maximum width in pixels (default: 800)")
    parser.add_argument("--quality", type=int, default=85,
                       help="WebP quality 0-100 (default: 85)")
    parser.add_argument("--replace", action="store_true",
                       help="Replace original files with optimized versions")
    
    args = parser.parse_args()
    
    optimize_restaurant_images(
        restaurant_images_dir=args.input_dir,
        output_dir=args.output_dir,
        max_width=args.max_width,
        quality=args.quality,
        replace_original=args.replace
    )

