"""
HeaderSelector: A 3-layer filtering pipeline to find the perfect restaurant header image.

The algorithm:
1. Technical Pass: Filter blurry, dark, or vertical images
2. Content Pass: Filter menus, bathroom selfies (handled by aesthetic model)
3. Aesthetic Pass: AI-powered quality scoring

Usage:
    selector = HeaderSelector()
    best_image = selector.pick_best_header([
        "photos/carbone_interior.jpg",
        "photos/blurry_menu.jpg",
        "photos/vertical_selfie.jpg",
        "photos/spicy_rigatoni.jpg"
    ])
"""

import cv2
import numpy as np
from PIL import Image
import torch
from typing import List, Optional, Tuple
import os

try:
    from transformers import AutoModelForImageClassification, AutoImageProcessor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[WARNING] transformers library not available. Aesthetic scoring will be disabled.", flush=True)


class HeaderSelector:
    def __init__(self, blur_threshold: int = 100, use_aesthetic: bool = True):
        """
        Initialize the HeaderSelector.
        
        Args:
            blur_threshold: Laplacian variance threshold for blur detection (lower = stricter)
            use_aesthetic: Whether to use AI aesthetic scoring (requires transformers)
        """
        self.blur_threshold = blur_threshold
        self.use_aesthetic = use_aesthetic and TRANSFORMERS_AVAILABLE
        
        self.model = None
        self.processor = None
        self.clip_model = None
        self.clip_processor = None
        
        if self.use_aesthetic:
            try:
                # Load a specialized "Aesthetic" model (Small and fast)
                # This model predicts a score from 1-10 on how "good" an image looks
                model_name = "cafeai/cafe_aesthetic"
                print(f"[LOAD] Loading aesthetic model: {model_name}...", flush=True)
                self.processor = AutoImageProcessor.from_pretrained(model_name)
                self.model = AutoModelForImageClassification.from_pretrained(model_name)
                print(f"[OK] Aesthetic model loaded", flush=True)
            except Exception as e:
                print(f"[WARNING] Failed to load aesthetic model: {e}", flush=True)
                print(f"   Falling back to basic scoring (no AI aesthetic)", flush=True)
                self.use_aesthetic = False

    def _is_blurry(self, image_path: str) -> bool:
        """
        Uses Laplacian Variance to detect blur.
        Low variance = Blurry. High variance = Sharp edges.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if image is blurry, False otherwise
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return True
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            return variance < self.blur_threshold
        except Exception as e:
            print(f"      [WARNING] Error checking blur for {image_path}: {e}", flush=True)
            return True  # Assume blurry if we can't check

    def _get_aspect_ratio_score(self, image_path: str) -> float:
        """
        Headers MUST be landscape. 
        Vertical images get a massive penalty.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Score between 0.0 and 1.0 (0 = disqualified, 1.0 = perfect 16:9)
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                ratio = width / height
                
                # If vertical (ratio < 1), return 0 (Disqualify)
                if ratio < 1.0:
                    return 0.0
                
                # Ideal header ratio is ~16:9 (1.77)
                # Reward 16:9, penalize square (1:1) or ultra-wide (3:1)
                dist_from_ideal = abs(ratio - 1.77)
                # Score: 1.0 for perfect 16:9, decreasing as ratio deviates
                # Still allow 4:3 (1.33) and 21:9 (2.33) but with lower scores
                if dist_from_ideal < 0.1:
                    return 1.0
                elif dist_from_ideal < 0.5:
                    return 0.8
                elif dist_from_ideal < 1.0:
                    return 0.5
                else:
                    return 0.2
        except Exception as e:
            print(f"      [WARNING] Error checking aspect ratio for {image_path}: {e}", flush=True)
            return 0.0

    def _get_brightness_score(self, image_path: str) -> float:
        """
        Check if image is too dark or too bright.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Score between 0.0 and 1.0 (0 = too dark/bright, 1.0 = good lighting)
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return 0.0
            
            # Convert to LAB color space and get L channel (lightness)
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]
            
            # Calculate mean brightness (0-100 scale in LAB)
            mean_brightness = np.mean(l_channel)
            
            # Ideal brightness is around 50-70 (not too dark, not too bright)
            if 50 <= mean_brightness <= 70:
                return 1.0
            elif 40 <= mean_brightness < 50 or 70 < mean_brightness <= 80:
                return 0.7
            elif 30 <= mean_brightness < 40 or 80 < mean_brightness <= 90:
                return 0.4
            else:
                return 0.1  # Too dark or too bright
        except Exception as e:
            print(f"      [WARNING] Error checking brightness for {image_path}: {e}", flush=True)
            return 0.5  # Neutral score if we can't check

    def _get_aesthetic_score(self, image_path: str) -> float:
        """
        Asks the AI: 'Is this photo professional quality?'
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Score between 0.0 and 1.0 (higher = more aesthetic)
        """
        if not self.use_aesthetic or not self.model or not self.processor:
            # Fallback: return neutral score if AI is not available
            return 0.5
        
        try:
            img = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=img, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                # The model outputs 2 classes: [Bad, Good]
                # We take the probability of 'Good'
                probs = torch.nn.functional.softmax(logits, dim=-1)
                score = probs[0][1].item()  # Score between 0.0 and 1.0
                return score
        except Exception as e:
            print(f"      [WARNING] Error getting aesthetic score for {image_path}: {e}", flush=True)
            return 0.3  # Low score if AI fails (likely a bad image)

    def _ensure_clip(self, verbose: bool = False) -> bool:
        """Lazy-load CLIP for text-image vibe matching."""
        if self.clip_model and self.clip_processor:
            return True
        try:
            from transformers import CLIPProcessor, CLIPModel

            if verbose:
                print("[LOAD] Loading CLIP model for vibe match...", flush=True)
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            return True
        except Exception as e:
            if verbose:
                print(f"[WARNING] CLIP unavailable: {e}", flush=True)
            return False

    def _clip_best_match(self, image_paths: List[str], text_prompt: str, verbose: bool = False) -> Optional[str]:
        """Return best image path matching text prompt using CLIP."""
        if not text_prompt or not image_paths:
            return None
        if not self._ensure_clip(verbose=verbose):
            return None
        try:
            imgs = [Image.open(p).convert("RGB") for p in image_paths]
            inputs = self.clip_processor(text=[text_prompt], images=imgs, return_tensors="pt", padding=True)
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image  # (num_images, 1)
                probs = logits_per_image.softmax(dim=0).squeeze()
                best_idx = probs.argmax().item()
                if verbose:
                    print(f"[CLIP] Best match idx {best_idx} prob {probs[best_idx]:.3f} for '{text_prompt}'", flush=True)
                return image_paths[best_idx]
        except Exception as e:
            if verbose:
                print(f"[WARNING] CLIP scoring failed: {e}", flush=True)
            return None

    def pick_best_header(self, image_paths: List[str], verbose: bool = True, text_prompt: Optional[str] = None) -> Optional[str]:
        """
        Pick the best header image from a list of image paths.
        
        Args:
            image_paths: List of paths to image files
            verbose: Whether to print progress messages
            
        Returns:
            Path to the best image, or None if all images failed filters
        """
        if not image_paths:
            if verbose:
                print("[WARNING] No images provided", flush=True)
            return None
        
        ranked_images = []
        
        for path in image_paths:
            if not os.path.exists(path):
                if verbose:
                    print(f"[SKIP] Skipping {path}: File not found", flush=True)
                continue
            
            # 1. FAIL FAST: Filter Blurry Images
            if self._is_blurry(path):
                if verbose:
                    print(f"[SKIP] Skipping {os.path.basename(path)}: Too blurry", flush=True)
                continue
            
            # 2. FAIL FAST: Filter Vertical Images
            aspect_score = self._get_aspect_ratio_score(path)
            if aspect_score == 0:
                if verbose:
                    print(f"[SKIP] Skipping {os.path.basename(path)}: Vertical orientation", flush=True)
                continue
            
            # 3. Technical Pass: Check brightness
            brightness_score = self._get_brightness_score(path)
            
            # 4. Aesthetic Pass: Calculate AI aesthetic score
            aesthetic_score = self._get_aesthetic_score(path)
            
            # 5. WEIGHTED TOTAL
            # Aesthetic matters most (50%), aspect ratio helps (30%), brightness matters (20%)
            if self.use_aesthetic:
                final_score = (aesthetic_score * 0.5) + (aspect_score * 0.3) + (brightness_score * 0.2)
            else:
                # Without AI, rely more on technical metrics
                final_score = (aspect_score * 0.6) + (brightness_score * 0.4)
            
            ranked_images.append((path, final_score, {
                'aesthetic': aesthetic_score,
                'aspect': aspect_score,
                'brightness': brightness_score
            }))
            
            if verbose:
                print(f"[OK] {os.path.basename(path)}: Score {final_score:.3f} (aesthetic={aesthetic_score:.2f}, aspect={aspect_score:.2f}, brightness={brightness_score:.2f})", flush=True)
        
        # Sort by score descending
        ranked_images.sort(key=lambda x: x[1], reverse=True)
        
        if not ranked_images:
            if verbose:
                print("[FAIL] All images failed filters", flush=True)
            return None
        
        winner_path = ranked_images[0][0]

        # Optional vibe match with CLIP
        if text_prompt:
            clip_choice = self._clip_best_match([p for p, _, _ in ranked_images], text_prompt, verbose=verbose)
            if clip_choice:
                winner_path = clip_choice
                if verbose:
                    print(f"[WINNER] CLIP-selected for '{text_prompt}': {os.path.basename(winner_path)}", flush=True)
        else:
            if verbose:
                print(f"\n[WINNER] Winner: {os.path.basename(winner_path)} (Score: {ranked_images[0][1]:.3f})", flush=True)
        
        return winner_path  # Return the path of the winner

    def pick_best_header_from_urls(self, image_urls: List[str], download_dir: str = "temp_header_selection",
                                   verbose: bool = True, text_prompt: Optional[str] = None) -> Optional[str]:
        """
        Download images from URLs, select the best one, and return its URL.
        
        Args:
            image_urls: List of image URLs
            download_dir: Temporary directory to download images
            verbose: Whether to print progress messages
            
        Returns:
            URL of the best image, or None if all images failed
        """
        import requests
        from pathlib import Path
        import hashlib
        from urllib.parse import urlparse
        
        if not image_urls:
            return None
        
        # Create temp directory
        temp_dir = Path(download_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_paths = []
        
        # Download images
        for idx, url in enumerate(image_urls[:20], 1):  # Limit to 20 images
            try:
                # Generate filename from URL
                parsed = urlparse(url)
                filename = parsed.path.split('/')[-1]
                if not filename or '.' not in filename:
                    filename = hashlib.md5(url.encode()).hexdigest() + '.jpg'
                
                # Clean filename
                if '?' in filename:
                    filename = filename.split('?')[0]
                
                temp_path = temp_dir / f"{idx:03d}_{filename}"
                
                # Download
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                downloaded_paths.append(str(temp_path))
                
                if verbose:
                    print(f"  [DOWNLOAD] Downloaded {idx}/{min(len(image_urls), 20)}: {filename}", flush=True)
            except Exception as e:
                if verbose:
                    print(f"  [WARNING] Failed to download {url}: {e}", flush=True)
                continue
        
        if not downloaded_paths:
            return None
        
        # Select best image
        best_path = self.pick_best_header(downloaded_paths, verbose=verbose, text_prompt=text_prompt)
        
        # Find corresponding URL
        if best_path:
            # Extract index from filename
            filename = os.path.basename(best_path)
            try:
                idx = int(filename.split('_')[0]) - 1
                if 0 <= idx < len(image_urls):
                    best_url = image_urls[idx]
                    
                    # Clean up temp files
                    try:
                        import shutil
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                    
                    return best_url
            except:
                pass
        
        # Clean up temp files
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass
        
        return None

