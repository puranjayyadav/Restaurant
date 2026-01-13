"""
Rank and fetch the best "Cloneable Adventures" itineraries from Supabase.
Refined for Plandit Production:
- Detects "Collection" vs "Linear" (if coordinates exist)
- Penalizes repetitive notes (Spam/Lazy detection)
- Uses Fuzzy Matching for smarter deduplication
"""

import json
import math
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests
from supabase import Client, create_client
from thefuzz import fuzz  # For smarter deduplication

# Set UTF-8 encoding for stdout to handle emojis
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not required if using environment variables directly

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://diytyziczzosylmyrfxo.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
TABLE_NAME = "lemon8_articles"
CLONEABLE_TABLE = "cloneable_adventures"
YELP_RESTAURANTS = "yelp_restaurants"
YELP_QUEUE = "crawl_queue_yelp"

# Header selector (optional)
HEADER_SELECTOR_AVAILABLE = False
try:
    from header_selector import HeaderSelector

    HEADER_SELECTOR_AVAILABLE = True
except Exception:
    HEADER_SELECTOR_AVAILABLE = False

@dataclass
class ScoreBreakdown:
    length_score: float
    notes_score: float
    keyword_score: float
    vibe_score: float
    spam_penalty: float
    total: float
    avg_note_length: float

@dataclass
class Adventure:
    source_id: Any
    title: str
    score: float
    score_breakdown: ScoreBreakdown
    stops_count: int
    stops: List[Dict[str, Any]]
    original_url: str
    tags: List[str] # New: ["Walking Tour", "City Guide", "Date Night"]


def generate_aesthetic_title(itinerary: Dict[str, Any], log_func=print) -> Dict[str, str]:
    """
    Uses an LLM (OpenRouter free models) to rename the itinerary.
    Returns {"new_title": "...", "subtitle": "..."} or empty dict on failure.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        log_func("[WARNING] OPENROUTER_API_KEY not set; skipping title generation")
        return {}

    # Minimal context to save tokens
    context = f"""
    Current Title: "{itinerary.get('title', '')}"
    Tags: {itinerary.get('tags', [])}
    Stops: {[s.get('place_name') for s in itinerary.get('stops', [])[:5]]} (First 5 stops)
    """

    system_prompt = """
    You are a creative copywriter for a travel app. Rename the itinerary to be short, aesthetic, and premium.
    Return ONLY a JSON object: {"new_title": "...", "subtitle": "..."}
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Cloneable Adventures Titling",
    }

    models_to_try = [
        "meta-llama/llama-3.2-3b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "tngtech/deepseek-r1t2-chimera:free",
        "kwaipilot/kat-coder-pro:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "tngtech/deepseek-r1t-chimera:free",
        "z-ai/glm-4.5-air:free",
        "tngtech/tng-r1t-chimera:free",
        "amazon/nova-2-lite-v1:free",
        "qwen/qwen3-coder:free",
        "google/gemma-3-27b-it:free",
        "openai/gpt-oss-20b:free",
    ]

    payload_base = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "max_tokens": 300,
    }

    for model in models_to_try:
        payload = payload_base.copy()
        payload["model"] = model
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60,
            )
            if response.status_code == 200:
                data = response.json()
                try:
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and parsed.get("new_title"):
                        log_func(f"[OK] Title generated via {model}")
                        return parsed
                except Exception:
                    pass
            elif response.status_code in (402, 429):
                log_func(f"[INFO] Model {model} unavailable ({response.status_code}), trying next")
                continue
            else:
                log_func(f"[WARNING] {model} returned {response.status_code}, trying next")
        except Exception as e:
            log_func(f"[WARNING] OpenRouter error for {model}: {e}")
            continue

    log_func("[WARNING] All models failed; keeping original title")
    return {}


def parse_yelp_id_from_url(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        m = re.search(r"yelp\\.com/biz/([^/?#]+)", url)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None


def fetch_yelp_images(supabase: Client, yelp_id: str) -> Dict[str, Any]:
    """Fetch image URLs for a Yelp place from Supabase."""
    try:
        res = (
            supabase.table(YELP_RESTAURANTS)
            .select("yelp_id, header_image_url, supabase_photos, photos, images, image_urls")
            .eq("yelp_id", yelp_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
    except Exception as e:
        print(f"[WARNING] Failed to fetch yelp images for {yelp_id}: {e}")
    return {}


def select_header_from_urls(image_urls: List[str], text_prompt: Optional[str] = None) -> Optional[str]:
    """Pick best header image from URLs using HeaderSelector (downloads to temp)."""
    if not image_urls:
        return None
    if HEADER_SELECTOR_AVAILABLE:
        try:
            selector = HeaderSelector(use_aesthetic=True)
            return selector.pick_best_header_from_urls(image_urls, verbose=False, text_prompt=text_prompt)
        except Exception as e:
            print(f"[WARNING] HeaderSelector error: {e}")
            return image_urls[0]
    # Fallback: first image
    return image_urls[0]


def flag_stop_for_images(
    supabase: Client, yelp_id: Optional[str], yelp_url: Optional[str], place_name: str
) -> None:
    """Add to crawl_queue_yelp with flag for cloneable adventures."""
    # If no yelp_id/url, slugify the place_name to create a queue entry
    if not yelp_id and not yelp_url:
        slug = re.sub(r"[^a-z0-9]+", "-", place_name.lower()).strip("-")
        if not slug:
            print(f"[SKIP] No yelp_id/url for {place_name}, cannot queue for images")
            return
        yelp_id = slug
        yelp_url = ""
    payload = {
        "yelp_id": yelp_id or place_name.replace(" ", "-").lower(),
        "url": yelp_url or "",
        "place_name": place_name,
        "status": "pending",
        "error_message": "flagged for cloneable adventures",
    }
    try:
        supabase.table(YELP_QUEUE).upsert(payload).execute()
        print(f"[QUEUE] Flagged {place_name} for image scraping")
    except Exception as e:
        print(f"[WARNING] Failed to queue {place_name} for images: {e}")

def calculate_geo_spread(stops: List[Dict[str, Any]]) -> float:
    """
    Returns the maximum distance (in km) between any two points in the itinerary.
    Requires 'lat' and 'lng' in the stops data. Returns 0.0 if missing.
    """
    coords = []
    for s in stops:
        # Check various places coordinates might live in your JSON structure
        lat = s.get('lat') or s.get('postgres_data', {}).get('lat')
        lng = s.get('lng') or s.get('postgres_data', {}).get('lng')
        
        if lat and lng:
            try:
                coords.append((float(lat), float(lng)))
            except (ValueError, TypeError):
                continue
                
    if len(coords) < 2:
        return 0.0
        
    # Simple bounding box approximation for speed (good enough for categorization)
    min_lat = min(c[0] for c in coords)
    max_lat = max(c[0] for c in coords)
    min_lng = min(c[1] for c in coords)
    max_lng = max(c[1] for c in coords)
    
    # Haversine-ish approximation
    # 1 deg lat ~ 111km, 1 deg lng ~ 85km (at NYC latitude)
    lat_diff = (max_lat - min_lat) * 111
    lng_diff = (max_lng - min_lng) * 85
    
    return math.sqrt(lat_diff**2 + lng_diff**2)

def calculate_adventure_score(itinerary: Dict[str, Any]) -> tuple[float, ScoreBreakdown, List[str]]:
    score = 0.0
    stops = itinerary.get("stops", [])
    title = itinerary.get("itinerary_title", "").lower()
    tags = []

    count = len(stops)
    if count < 4:
        return 0.0, ScoreBreakdown(0,0,0,0,0,0,0), []

    # --- 1. LENGTH SCORE ---
    length_score = 0.0
    if 4 <= count <= 8:
        length_score = 30
        score += 30
    elif 9 <= count <= 12:
        length_score = 20
        score += 20
    else:
        length_score = 10
        score += 10

    # --- 2. NOTES SCORE ---
    notes_list = [s.get("notes", "").strip() for s in stops]
    total_note_len = sum(len(n) for n in notes_list)
    avg_note_len = total_note_len / count if count else 0
    
    notes_score = 0.0
    if avg_note_len > 80: notes_score = 40
    elif avg_note_len > 30: notes_score = 20
    else: notes_score = 5
    score += notes_score

    # --- 3. KEYWORD & VIBE SCORE ---
    high_value_keywords = ["guide", "itinerary", "crawl", "tour", "day in", "weekend"]
    keyword_score = 0.0
    if any(k in title for k in high_value_keywords):
        keyword_score = 20
        score += 20

    vibe_keywords = {
        "date": "🍷 Date Night",
        "hidden": "🌿 Hidden Gems",
        "speakeasy": "🍸 Speakeasy",
        "aesthetic": "📸 Photo Ops",
        "cheap": "🌮 Cheap Eats",
        "free": "🌮 Cheap Eats",
        "coffee": "☕️ Coffee Run",
        "brunch": "🥐 Brunch"
    }
    
    vibe_score = 0.0
    for kw, tag in vibe_keywords.items():
        if kw in title:
            vibe_score = 10
            if tag not in tags: tags.append(tag)
            
    if vibe_score > 0: score += 10 # Cap bonus at 10

    # --- 4. SPAM PENALTY (New!) ---
    # Check for duplicate notes (Lazy scraping or lazy user)
    unique_notes = set(notes_list)
    spam_penalty = 0.0
    
    # If >50% of notes are identical, it's low quality
    if len(unique_notes) < (count * 0.5):
        spam_penalty = -50
        score += spam_penalty
        tags.append("⚠️ Repetitive Content")

    # --- 5. GEOGRAPHIC CLASSIFICATION ---
    spread_km = calculate_geo_spread(stops)
    if spread_km > 0:
        if spread_km < 3.0: # Everything within 3km
            tags.append("🚶 Walkable")
        elif spread_km > 8.0: # Spans >8km (e.g. Bronx to Brooklyn)
            tags.append("🚕 City Guide") # Requires Uber/Subway
        else:
            tags.append("🚇 Metro Hop")
            
    breakdown = ScoreBreakdown(
        length_score=length_score,
        notes_score=notes_score,
        keyword_score=keyword_score,
        vibe_score=vibe_score,
        spam_penalty=spam_penalty,
        total=max(0, score), # No negative scores
        avg_note_length=avg_note_len
    )
    return max(0, score), breakdown, tags


def parse_json_field(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return []
    return []


def resolve_header_image_for_stops(stops: List[Dict[str, Any]], supabase: Client, text_prompt: Optional[str] = None) -> Optional[str]:
    """
    Find a header image by checking each stop's Yelp images.
    If none exist, queue the stop for image scraping.
    """
    for stop in stops:
        place_name = stop.get("place_name") or stop.get("name") or "unknown"
        yelp_id = stop.get("yelp_id") or parse_yelp_id_from_url(stop.get("url") or stop.get("yelp_url") or "")
        yelp_url = stop.get("url") or stop.get("yelp_url") or ""

        if not yelp_id and yelp_url:
            yelp_id = parse_yelp_id_from_url(yelp_url)

        header_candidates: List[str] = []

        if yelp_id:
            record = fetch_yelp_images(supabase, yelp_id)
            if record:
                if record.get("header_image_url"):
                    header_candidates.append(record["header_image_url"])

                for key in ["supabase_photos", "photos", "images", "image_urls"]:
                    vals = parse_json_field(record.get(key))
                    for v in vals:
                        if isinstance(v, str) and v.startswith("http"):
                            header_candidates.append(v)

        # Deduplicate
        seen = set()
        header_candidates = [u for u in header_candidates if not (u in seen or seen.add(u))]

        if header_candidates:
            best = select_header_from_urls(header_candidates, text_prompt=text_prompt)
            if best:
                return best

        # If no images, queue for scraping
        flag_stop_for_images(supabase, yelp_id, yelp_url, place_name)

    return None

def fetch_candidates(supabase: Client) -> List[Adventure]:
    print("Fetching raw articles from Supabase...")
    response = (
        supabase.table(TABLE_NAME)
        .select("url, itinerary_data") # Specific columns for speed
        .not_.is_("itinerary_data", "null")
        .execute()
    )

    candidates = []
    for row in response.data or []:
        try:
            raw_data = row["itinerary_data"]
            data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        except (json.JSONDecodeError, TypeError):
            continue

        if data.get("city") != "New York": continue
        if len(data.get("stops", [])) < 4: continue

        score, breakdown, tags = calculate_adventure_score(data)
        
        # ID Handling - use url as source_id since it's the primary key
        source_id = row.get("url")

        candidates.append(
            Adventure(
                source_id=source_id,
                title=data.get("itinerary_title", "Untitled"),
                score=score,
                score_breakdown=breakdown,
                stops_count=len(data["stops"]),
                stops=data["stops"],
                original_url=row.get("url", ""),
                tags=tags
            )
        )
    return candidates

def dedupe_smartly(adventures: List[Adventure], max_results: int = 20) -> List[Adventure]:
    """
    Uses Fuzzy Matching to remove duplicates like:
    "NYC Date Night" vs "Date Night in NYC"
    """
    unique_adventures = []
    
    # Sort by score first so high quality versions win
    sorted_adv = sorted(adventures, key=lambda x: x.score, reverse=True)
    
    for current in sorted_adv:
        is_duplicate = False
        for kept in unique_adventures:
            # Ratio > 85 means they are very similar
            similarity = fuzz.token_sort_ratio(current.title, kept.title)
            
            if similarity > 85:
                is_duplicate = True
                # Optional: If the new one has better notes, swap it? 
                # For now, first-to-keep (highest score) logic applies.
                break
        
        if not is_duplicate:
            unique_adventures.append(current)
            
        if len(unique_adventures) >= max_results:
            break
            
    return unique_adventures


def upsert_cloneable_adventure(
    supabase: Client,
    adventure: Adventure,
    new_title: str,
    subtitle: str,
    header_image_url: Optional[str],
) -> None:
    payload = {
        "source_id": adventure.source_id,
        "title": adventure.title,
        "new_title": new_title or adventure.title,
        "subtitle": subtitle or "",
        "tags": adventure.tags,
        "score": adventure.score,
        "score_breakdown": asdict(adventure.score_breakdown),
        "stops": adventure.stops,
        "original_url": adventure.original_url,
        "header_image_url": header_image_url,
    }
    supabase.table(CLONEABLE_TABLE).upsert(payload).execute()

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Warning: Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    candidates = fetch_candidates(supabase)
    print(f"Fetched {len(candidates)} raw candidates.")

    unique_top = dedupe_smartly(candidates, max_results=20)

    print(f"\n{'='*60}")
    print(f"Writing {len(unique_top)} cloneable adventures to Supabase")
    print(f"{'='*60}\n")

    for i, adv in enumerate(unique_top, 1):
        print(f"[{i}/{len(unique_top)}] {adv.title} ({adv.score:.0f} pts)")

        # LLM title/subtitle
        title_payload = generate_aesthetic_title(
            {"title": adv.title, "tags": adv.tags, "stops": adv.stops},
            log_func=print,
        )
        new_title = title_payload.get("new_title", adv.title)
        subtitle = title_payload.get("subtitle", "")

        # Header image (vibe match with title)
        header_image_url = resolve_header_image_for_stops(adv.stops, supabase, text_prompt=new_title)
        if header_image_url:
            print(f"   [HEADER] {header_image_url[:70]}...")
        else:
            print("   [HEADER] None (queued missing stops)")

        # Save to Supabase
        try:
            upsert_cloneable_adventure(supabase, adv, new_title, subtitle, header_image_url)
            print("   [OK] Saved to cloneable_adventures")
        except Exception as e:
            print(f"   [WARNING] Failed to save: {e}")

if __name__ == "__main__":
    main()