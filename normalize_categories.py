"""
Category Normalizer for Lemon8 Places Data.

Uses LLM to convert messy categories like "Cookies Details" into standardized taxonomy.
This fixes the "Cookies Details" pollution bug where Yelp cookie notices got scraped as categories.

Usage:
    python normalize_categories.py [--dry-run] [--limit 100]
"""

import json
import os
import sys
import argparse
import time
from typing import Literal, Optional, List, Dict, Any
from dataclasses import dataclass

import requests
from supabase import create_client, Client

# Set UTF-8 encoding
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://diytyziczzosylmyrfxo.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ============================================================================
# MASTER TAXONOMY - The "Menu" of valid categories
# ============================================================================
VALID_CATEGORIES = [
    # Food
    "Coffee & Tea",
    "Bakery",
    "Breakfast & Brunch",
    "Lunch",
    "Dinner",
    "Pizza",
    "Asian",
    "Latin",
    "Italian",
    "Seafood",
    "Steakhouse",
    "Dessert",
    "Fast Food",
    
    # Drink / Nightlife
    "Bar",
    "Cocktail Bar",
    "Wine Bar",
    "Rooftop",
    "Club",
    "Brewery",
    
    # Activities
    "Park",
    "Museum",
    "Gallery",
    "Shopping",
    "Entertainment",
    "Landmark",
    "Hotel",
    "Spa",
    "Gym",
    
    # Catch-all
    "Neighborhood",
    "Photo Spot",
    "Other"
]

# Quick fix mappings - no LLM needed for obvious cases
QUICK_FIX_MAPPINGS = {
    # The infamous scraping bugs
    "cookies details": "Dessert",
    "cookie details": "Dessert",
    
    # Generic food
    "food": "Dinner",
    "restaurant": "Dinner",
    
    # Coffee & Tea
    "cafe": "Coffee & Tea",
    "café": "Coffee & Tea",
    "coffee": "Coffee & Tea",
    "tea house": "Coffee & Tea",
    "matcha": "Coffee & Tea",
    
    # Bars & Nightlife
    "bar": "Bar",
    "pub": "Bar",
    "rooftop bar": "Rooftop",
    "rooftop": "Rooftop",
    "cocktail bar": "Cocktail Bar",
    "cocktail": "Cocktail Bar",
    "speakeasy": "Cocktail Bar",
    "wine bar": "Wine Bar",
    "club": "Club",
    "nightclub": "Club",
    "lounge": "Cocktail Bar",
    "brewery": "Brewery",
    
    # Food types
    "pizza": "Pizza",
    "pizzeria": "Pizza",
    "bakery": "Bakery",
    "dessert": "Dessert",
    "ice cream": "Dessert",
    "cookies": "Dessert",
    "donut": "Dessert",
    "brunch": "Breakfast & Brunch",
    "breakfast": "Breakfast & Brunch",
    "lunch": "Lunch",
    "dinner": "Dinner",
    "fine dining": "Dinner",
    
    # Cuisines
    "sushi": "Asian",
    "ramen": "Asian",
    "japanese": "Asian",
    "chinese": "Asian",
    "thai": "Asian",
    "korean": "Asian",
    "vietnamese": "Asian",
    "dim sum": "Asian",
    "mexican": "Latin",
    "tacos": "Latin",
    "peruvian": "Latin",
    "italian": "Italian",
    "pasta": "Italian",
    "seafood": "Seafood",
    "steak": "Steakhouse",
    "steakhouse": "Steakhouse",
    
    # Activities & Places
    "park": "Park",
    "garden": "Park",
    "museum": "Museum",
    "gallery": "Gallery",
    "art gallery": "Gallery",
    "hotel": "Hotel",
    "shopping": "Shopping",
    "store": "Shopping",
    "market": "Shopping",
    "dining hall": "Shopping",  # Like Eataly
    "food hall": "Shopping",
    "theater": "Entertainment",
    "theatre": "Entertainment",
    "comedy": "Entertainment",
    "jazz": "Entertainment",
    "show": "Entertainment",
    "tour": "Entertainment",
    "landmark": "Landmark",
    "monument": "Landmark",
    "photo spot": "Photo Spot",
    "spa": "Spa",
    "gym": "Gym",
    
    # These should NOT be Entertainment
    "neighborhood": "Neighborhood",
    "walk": "Neighborhood",
    "walking": "Neighborhood",
    "explore": "Neighborhood",
}

# Name patterns that indicate Neighborhood (for places like "SoHo", "Greenwich Village")
NEIGHBORHOOD_NAMES = {
    "soho", "tribeca", "nolita", "noho", "dumbo", "brooklyn heights",
    "williamsburg", "greenpoint", "bushwick", "bed-stuy", "harlem",
    "chelsea", "west village", "east village", "greenwich village",
    "lower east side", "les", "upper east side", "ues", "upper west side", "uws",
    "midtown", "times square", "flatiron", "gramercy", "murray hill",
    "chinatown", "little italy", "koreatown", "hells kitchen",
    "financial district", "fidi", "battery park", "meatpacking",
}


@dataclass
class NormalizationResult:
    place_name: str
    old_category: str
    new_category: str
    confidence: float
    method: str  # "quick_fix" or "llm"


def get_supabase_client() -> Client:
    """Create Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def quick_fix_category(category: str, place_name: str = "") -> Optional[str]:
    """
    Try to fix category without LLM using simple mappings.
    Returns None if LLM is needed.
    """
    name_lower = place_name.lower().strip()
    category_lower = (category or "").lower().strip()
    
    # =====================================================================
    # STEP 1: Name-based inference FIRST (most reliable)
    # These patterns are very specific and should override category
    # =====================================================================
    
    # Museums & Science Centers (before neighborhood check!)
    if "museum" in name_lower or "science center" in name_lower or "observatory" in name_lower:
        return "Museum"
    
    # Markets & Shopping
    if "market" in name_lower or "farmer" in name_lower or "flea" in name_lower:
        return "Shopping"
    
    # Diners and restaurants
    if "diner" in name_lower:
        return "Dinner"
    
    # Food & Drink by name
    if "pizza" in name_lower or "pizzeria" in name_lower:
        return "Pizza"
    if "bagel" in name_lower:
        return "Bakery"
    if "bakery" in name_lower or "pastry" in name_lower or "patisserie" in name_lower:
        return "Bakery"
    if "coffee" in name_lower:
        return "Coffee & Tea"
    if "cafe" in name_lower or "café" in name_lower:
        return "Coffee & Tea"
    if "rooftop" in name_lower:
        return "Rooftop"
    if "cocktail" in name_lower or "speakeasy" in name_lower:
        return "Cocktail Bar"
    if "wine bar" in name_lower:
        return "Wine Bar"
    if "bar " in name_lower or name_lower.endswith(" bar"):
        if "chocolate" not in name_lower and "salad" not in name_lower:
            return "Bar"
    if "sushi" in name_lower or "ramen" in name_lower or "izakaya" in name_lower:
        return "Asian"
    if "taco" in name_lower or "burrito" in name_lower or "mexican" in name_lower:
        return "Latin"
    
    # Activities & Places by name
    if "park" in name_lower and "parking" not in name_lower:
        return "Park"
    if "garden" in name_lower and "beer garden" not in name_lower:
        return "Park"
    if "hotel" in name_lower or " inn " in name_lower or name_lower.endswith(" inn"):
        return "Hotel"
    if "gallery" in name_lower:
        return "Gallery"
    if "theater" in name_lower or "theatre" in name_lower:
        return "Entertainment"
    if " tour" in name_lower or name_lower.startswith("tour "):
        return "Entertainment"
    if "spa " in name_lower or name_lower.endswith(" spa"):
        return "Spa"
    
    # Landmarks by name
    if any(x in name_lower for x in ["statue", "bridge", "tower", "memorial"]):
        return "Landmark"
    
    # =====================================================================
    # STEP 2: Check if place name IS a neighborhood (SoHo, Greenwich Village)
    # =====================================================================
    for neighborhood in NEIGHBORHOOD_NAMES:
        if name_lower == neighborhood or name_lower.startswith(neighborhood + " "):
            return "Neighborhood"
    
    # Generic short names with "Activity" category are usually neighborhoods
    # But exclude anything with specific keywords
    if category_lower == "activity" and len(name_lower.split()) <= 2:
        exclude_words = ["tour", "show", "class", "museum", "park", "market", 
                        "center", "studio", "club", "bar", "cafe", "diner"]
        if not any(word in name_lower for word in exclude_words):
            return "Neighborhood"
    
    # =====================================================================
    # STEP 3: Category-based mapping
    # =====================================================================
    
    # Direct mapping from category
    if category_lower in QUICK_FIX_MAPPINGS:
        return QUICK_FIX_MAPPINGS[category_lower]
    
    # Partial matching on category
    for key, value in QUICK_FIX_MAPPINGS.items():
        if key in category_lower:
            return value
    
    # Check if already valid
    if category in VALID_CATEGORIES:
        return category
    
    # =====================================================================
    # STEP 4: Plaza/Square landmarks
    # =====================================================================
    if "plaza" in name_lower or "square" in name_lower:
        # Could be landmark or neighborhood - check category
        if category_lower == "activity":
            return "Landmark"
    
    return None  # Needs LLM


def normalize_with_llm(
    place_name: str,
    current_category: str,
    vibe_tags: List[str],
    notes: str = "",
    types: List[str] = None
) -> Dict[str, Any]:
    """
    Use LLM to normalize the category.
    Returns {"category": "...", "confidence": 0.0-1.0}
    """
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY not set")
        return {"category": "Other", "confidence": 0.0}
    
    # Build context for the LLM
    context = f"""
Place Name: "{place_name}"
Current Category (possibly wrong): "{current_category}"
Vibe Tags: {vibe_tags}
Types/Tags: {types or []}
Notes: "{notes[:200] if notes else ''}"
"""
    
    system_prompt = f"""You are a data cleaning expert. Your job is to categorize places into a FIXED taxonomy.

VALID CATEGORIES (pick EXACTLY ONE):
{json.dumps(VALID_CATEGORIES, indent=2)}

RULES:
1. "Cookies Details" is ALWAYS wrong - it's a scraping bug from Yelp cookie notices.
2. Use the place NAME as the strongest signal (e.g., "John's of Bleecker Street" = Pizza)
3. Use vibe_tags as hints (e.g., "Wine-Friendly" = Wine Bar or Dinner)
4. If unsure, pick the most likely food/drink category based on the name.
5. "Neighborhood" is for walking tours or area guides, not restaurants.

Return ONLY a JSON object: {{"category": "...", "confidence": 0.0-1.0}}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Category Normalizer",
    }
    
    # Models to try (in order of preference)
    models = [
        "kwaipilot/kat-coder-pro:free",  # User requested
        "meta-llama/llama-3.2-3b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-3-27b-it:free",
    ]
    
    payload_base = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ],
        "temperature": 0.1,  # Low temp for consistent classification
        "max_tokens": 100,
    }
    
    for model in models:
        payload = {**payload_base, "model": model}
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Parse JSON from response
                try:
                    # Handle markdown code blocks
                    if "```" in content:
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    
                    result = json.loads(content.strip())
                    
                    # Validate category is in our taxonomy
                    category = result.get("category", "Other")
                    if category not in VALID_CATEGORIES:
                        # Find closest match
                        category_lower = category.lower()
                        for valid in VALID_CATEGORIES:
                            if valid.lower() in category_lower or category_lower in valid.lower():
                                category = valid
                                break
                        else:
                            category = "Other"
                    
                    return {
                        "category": category,
                        "confidence": float(result.get("confidence", 0.8))
                    }
                    
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[WARNING] Failed to parse LLM response: {content[:100]}")
                    continue
                    
            elif response.status_code in (402, 429):
                print(f"[INFO] Model {model} rate limited, trying next...")
                continue
            else:
                print(f"[WARNING] {model} returned {response.status_code}")
                continue
                
        except Exception as e:
            print(f"[WARNING] LLM error with {model}: {e}")
            continue
    
    # All models failed
    return {"category": "Other", "confidence": 0.0}


def fetch_places_needing_normalization(supabase: Client, limit: int = 100, article_url_filter: Optional[str] = None) -> List[Dict]:
    """
    Fetch places from lemon8_articles that have bad categories.
    """
    print(f"Fetching places with 'Cookies Details' or missing categories...")
    
    query = supabase.table("lemon8_articles") \
        .select("url, enriched_itinerary_data") \
        .not_.is_("enriched_itinerary_data", "null")
    
    if article_url_filter:
        query = query.eq("url", article_url_filter)

    response = query.limit(500).execute()
    
    places_to_fix = []
    
    for row in response.data or []:
        data = row.get("enriched_itinerary_data")
        if isinstance(data, list) and data:
            data = data[0]
        if not data:
            continue
        
        article_url = row.get("url")

        print(f"Processing article: {article_url}")
        print(f"Raw enriched_itinerary_data: {json.dumps(data, indent=2)}")
        
        for i, stop in enumerate(data.get("stops", [])):
            solver_data = stop.get("solver_data", {})
            category = solver_data.get("category_normalized", "")
            
            # Check if this needs fixing
            needs_fix = False
            if not category:
                needs_fix = True
            elif "cookie" in category.lower():
                needs_fix = True
            elif category not in VALID_CATEGORIES:
                needs_fix = True
            
            if needs_fix:
                places_to_fix.append({
                    "article_url": article_url,
                    "stop_index": i,
                    "place_name": stop.get("name") or stop.get("place_name") or "Unknown",
                    "current_category": category,
                    "vibe_tags": solver_data.get("vibe_tags", []),
                    "notes": stop.get("notes", ""),
                    "types": stop.get("types", []),
                    "solver_data": solver_data,
                    "full_stop": stop,
                })
                
                if len(places_to_fix) >= limit:
                    break
        
        if len(places_to_fix) >= limit:
            break
    
    return places_to_fix


def update_place_category(
    supabase: Client,
    article_url: str,
    stop_index: int,
    new_category: str,
    dry_run: bool = False
) -> bool:
    """
    Update the category_normalized field for a specific stop.
    """
    if dry_run:
        return True
    
    try:
        # Fetch current data
        response = (
            supabase.table("lemon8_articles")
            .select("enriched_itinerary_data")
            .eq("url", article_url)
            .single()
            .execute()
        )
        
        data = response.data.get("enriched_itinerary_data")
        if isinstance(data, list) and data:
            data = data[0]
        
        if not data or "stops" not in data:
            return False
        
        # Update the specific stop
        if stop_index < len(data["stops"]):
            stop = data["stops"][stop_index]
            if "solver_data" not in stop:
                stop["solver_data"] = {}
            stop["solver_data"]["category_normalized"] = new_category

            # Also update the new top-level array columns
            # Aggregate all categories and vibes from all stops in the itinerary
            all_categories = []
            all_vibes = []
            for s in data["stops"]:
                if "solver_data" in s and "category_normalized" in s["solver_data"]:
                    all_categories.append(s["solver_data"]["category_normalized"])
                if "solver_data" in s and "vibe_tags" in s["solver_data"]:
                    all_vibes.extend(s["solver_data"]["vibe_tags"])

            # Remove duplicates and ensure unique values
            unique_categories = list(set(c for c in all_categories if c))
            unique_vibes = list(set(v for v in all_vibes if v))
            
            # Save back
            supabase.table("lemon8_articles").update({
                "enriched_itinerary_data": [data],
                "contained_categories": unique_categories,
                "contained_vibes": unique_vibes,
            }).eq("url", article_url).execute()
            
            return True
            
    except Exception as e:
        print(f"[ERROR] Failed to update {article_url}: {e}")
        return False
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Normalize place categories using LLM")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually update the database")
    parser.add_argument("--limit", type=int, default=50, help="Max places to process")
    parser.add_argument("--skip-llm", action="store_true", help="Only use quick fixes, no LLM")
    parser.add_argument("--url", type=str, help="Process only a specific article URL")
    args = parser.parse_args()
    
    print("=" * 60)
    print("CATEGORY NORMALIZER")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Limit: {args.limit}")
    print(f"LLM: {'DISABLED' if args.skip_llm else 'ENABLED'}")
    print(f"URL Filter: {args.url if args.url else 'None'}")
    print("=" * 60)
    
    supabase = get_supabase_client()
    
    # Fetch places needing normalization
    places = fetch_places_needing_normalization(supabase, limit=args.limit, article_url_filter=args.url)
    print(f"Found {len(places)} places needing normalization\n")
    
    if not places:
        print("Nothing to fix!")
        return
    
    results: List[NormalizationResult] = []
    
    for i, place in enumerate(places, 1):
        place_name = place["place_name"]
        old_category = place["current_category"]
        
        print(f"[{i}/{len(places)}] {place_name}")
        print(f"   Old: '{old_category}'")
        
        # Try quick fix first
        new_category = quick_fix_category(old_category, place_name)
        method = "quick_fix"
        confidence = 1.0
        
        if new_category is None and not args.skip_llm:
            # Need LLM
            print(f"   Using LLM...")
            llm_result = normalize_with_llm(
                place_name=place_name,
                current_category=old_category,
                vibe_tags=place["vibe_tags"],
                notes=place["notes"],
                types=place["types"]
            )
            new_category = llm_result["category"]
            confidence = llm_result["confidence"]
            method = "llm"
            time.sleep(0.5)  # Rate limit
        elif new_category is None:
            new_category = "Other"
            confidence = 0.0
            method = "fallback"
        
        print(f"   New: '{new_category}' ({method}, {confidence:.0%})")
        
        # Update database
        if old_category != new_category:
            success = update_place_category(
                supabase,
                place["article_url"],
                place["stop_index"],
                new_category,
                dry_run=args.dry_run
            )
            status = "✓" if success else "✗"
        else:
            status = "="  # No change needed
        
        print(f"   Status: {status}")
        
        results.append(NormalizationResult(
            place_name=place_name,
            old_category=old_category,
            new_category=new_category,
            confidence=confidence,
            method=method
        ))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    quick_fixes = sum(1 for r in results if r.method == "quick_fix")
    llm_fixes = sum(1 for r in results if r.method == "llm")
    changes = sum(1 for r in results if r.old_category != r.new_category)
    
    print(f"Total processed: {len(results)}")
    print(f"Quick fixes: {quick_fixes}")
    print(f"LLM fixes: {llm_fixes}")
    print(f"Categories changed: {changes}")
    
    # Show category distribution
    print("\nNew category distribution:")
    category_counts = {}
    for r in results:
        category_counts[r.new_category] = category_counts.get(r.new_category, 0) + 1
    
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
