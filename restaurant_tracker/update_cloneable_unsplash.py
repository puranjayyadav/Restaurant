"""
Fetch unique Unsplash cover images for cloneable_adventures without header_image_url
and update the table. Prevents duplicate images across rows.
"""

import os
import requests
import sys
import time
from typing import Optional, Set

try:
    from supabase_config import get_supabase_client
except Exception as e:
    raise SystemExit(f"Failed to import supabase_config: {e}")

# Global set to track used image URLs in this session
SEEN_URLS: Set[str] = set()

def get_unique_unsplash_image(
    base_query: str, 
    access_key: str, 
    attempt: int = 0
) -> Optional[str]:
    """
    Fetches a photo, checking against global SEEN_URLS to ensure uniqueness.
    Recursively tries varied queries if duplicates are found.
    """
    
    # 1. Query Variations (The Vibe Shifter)
    # If the first attempt fails or is a duplicate, we shift the query slightly
    variations = [
        f"{base_query}",                                # 1. "soho cafe aesthetic"
        f"{base_query} detail",                         # 2. "soho cafe aesthetic detail"
        f"{base_query} vertical",                       # 3. "soho cafe aesthetic vertical"
        f"{base_query.split()[0]} nyc aesthetic",       # 4. "soho nyc aesthetic" (fallback to neighborhood)
        f"new york city {base_query.split()[-1]}"       # 5. "new york city aesthetic" (broad fallback)
    ]

    if attempt >= len(variations):
        print(f"[GIVE UP] Could not find unique image for '{base_query}' after {len(variations)} tries.")
        return None

    current_query = variations[attempt]
    
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": current_query,
        "orientation": "portrait",
        "per_page": 10, # Fetch more to increase odds of finding a unique one
        "order_by": "relevant",
        "content_filter": "high"
    }
    headers = {"Authorization": f"Client-ID {access_key}"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        
        if resp.status_code != 200:
            print(f"[WARN] Unsplash HTTP {resp.status_code} for '{current_query}'")
            return None

        results = resp.json().get("results", [])
        if not results:
            print(f"[WARN] No results for '{current_query}'. Retrying...")
            return get_unique_unsplash_image(base_query, access_key, attempt + 1)

        # 2. The Uniqueness Check
        for photo in results:
            img_url = photo.get("urls", {}).get("regular")
            if img_url and img_url not in SEEN_URLS:
                SEEN_URLS.add(img_url) # Mark as used
                return img_url
        
        # If we loop through all 10 and they are ALL seen, recurse with new query
        print(f"[DUPE] All 10 results were duplicates for '{current_query}'. Retrying...")
        return get_unique_unsplash_image(base_query, access_key, attempt + 1)

    except Exception as e:
        print(f"[ERROR] {current_query}: {e}")
        return None


def clean_title_for_unsplash(title: str, city: str = "New York") -> str:
    q = title.lower()
    # Logic matches your original categorizer
    if "coffee" in q or "cafe" in q or "latte" in q:
        return f"{city} cafe aesthetic"
    if "date" in q or "romantic" in q or "night" in q:
        return f"{city} night street aesthetic"
    if "bar" in q or "speakeasy" in q or "drink" in q:
        return f"{city} cocktail bar interior"
    if "museum" in q or "art" in q or "gallery" in q:
        return f"{city} museum architecture"
    if "vintage" in q or "thrift" in q or "shopping" in q:
        return f"{city} fashion street style"
    if "food" in q or "eat" in q or "pizza" in q or "bagel" in q:
        return f"{city} food photography"
    
    hoods = ["soho", "williamsburg", "west village", "greenwich", "chelsea", "dumbo", "chinatown", "tribeca"]
    for hood in hoods:
        if hood in q:
            return f"{hood} {city} street"
            
    return f"{city} city aesthetic vertical"


def main():
    def safe(msg: str):
        try:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", "ignore"))
        except Exception:
            pass

    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        raise SystemExit("Set UNSPLASH_ACCESS_KEY environment variable.")

    supabase = get_supabase_client()
    if not supabase:
        raise SystemExit("Missing Supabase credentials.")

    # 1. Load existing images into SEEN_URLS to avoid repeating what's already in DB
    # (Optional: Only if you want strict uniqueness against previous runs)
    # existing_rows = supabase.table("cloneable_adventures").select("header_image_url").not_.is_("header_image_url", "null").execute()
    # for r in existing_rows.data:
    #     if r.get('header_image_url'): SEEN_URLS.add(r['header_image_url'])

    rows = (
        supabase.table("cloneable_adventures")
        .select("source_id, title, header_image_url")
        .limit(5000)  # refresh all, adjust as needed
        .execute()
        .data
        or []
    )
    safe(f"Loaded {len(rows)} adventures for header_image_url refresh")

    updated = 0
    for row in rows:
        title = row.get("title") or row.get("source_id")
        source_id = row.get("source_id")
        
        if not title or not source_id:
            continue

        base_query = clean_title_for_unsplash(title)
        
        # Use the new Unique Getter
        img_url = get_unique_unsplash_image(base_query, access_key)

        if not img_url:
            continue

        supabase.table("cloneable_adventures").update({"header_image_url": img_url}).eq(
            "source_id", source_id
        ).execute()
        
        updated += 1
        safe(f"[OK] {title} -> {img_url}")
        
        # Polite rate limiting
        time.sleep(0.5)

    safe(f"Done. Updated {updated} rows.")

if __name__ == "__main__":
    main()