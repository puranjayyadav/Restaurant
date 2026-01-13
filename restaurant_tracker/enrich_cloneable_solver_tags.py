"""
Enrich existing cloneable_adventures stops with solver-ready tags.

Adds a `solver_data` block to each stop:
{
  "time_bias": "Evening",
  "duration_minutes": 90,
  "vibe_tags": [...],
  "price_tier": "$$",
  "category_normalized": "Coffee"
}

Run:
  OPENAI_API_KEY=... SUPABASE_URL=... SUPABASE_SERVICE_KEY=... \
    python enrich_cloneable_solver_tags.py --limit 20

Use --dry-run to preview without writing.
"""

from __future__ import annotations

import argparse
import os
import time
import json # Import json for pretty printing
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from supabase_config import get_supabase_client


class SolverTags(BaseModel):
    time_bias: str = Field(..., description="Morning, Daytime, Evening, Late Night, Anytime")
    duration_minutes: int = Field(..., description="Estimated minutes spent here")
    vibe_tags: List[str] = Field(..., description="3-5 vibe descriptors")
    price_tier: str = Field(..., description="$, $$, $$$, $$$$")
    category_normalized: str = Field(..., description="Standard category label e.g., Coffee, Bar")


def build_prompt(stop: Dict[str, Any], itinerary_title: str) -> str:
    parts = []
    name = stop.get("place_name") or stop.get("name") or "Unknown"
    parts.append(f"Place: {name}")
    parts.append(f"Itinerary: {itinerary_title}")

    hints = []
    for key in ["notes", "tip", "insider_tip", "description", "category", "vibe", "type", "tag"]:
        val = stop.get(key)
        if val:
            hints.append(f"{key}: {val}")

    price = stop.get("price_range") or stop.get("price") or stop.get("pricing")
    if price:
        hints.append(f"price_hint: {price}")

    tags = stop.get("tags")
    if tags:
        hints.append(f"tags_hint: {tags}")

    if hints:
        parts.append("Context:\n" + "\n".join(f"- {h}" for h in hints))

    return "\n".join(parts)


SYSTEM_PROMPT = """
You are a Data Enrichment Engine for a travel app.
Classify each place into the solver taxonomy.

Rules:
- time_bias: Morning (coffee/bakery/breakfast), Daytime (parks/shops/museums/lunch),
  Evening (bars/clubs/dinner), Late Night (after 10pm nightlife), Anytime if unclear.
- duration_minutes: realistic avg time on-site (coffee 25-40, lunch 60, dinner 90,
  bar/drinks 60-120, museum 90-150, quick stop 15-30).
- vibe_tags: 3-5 adjectives (Cozy, Romantic, Lively, Solo Friendly, Work Friendly, Trendy, Quiet).
- price_tier: $, $$, $$$, $$$$ inferred from hints.
- category_normalized: compact label (Coffee, Bakery, Brunch, Lunch, Dinner, Bar, Cocktail Bar,
  Wine Bar, Cafe, Dessert, Park, Museum, Shop, Activity, Music, Nightlife).
Return strictly the JSON object.
"""


OPENROUTER_MODEL = "kwaipilot/kat-coder-pro:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_solver_tags(stop: Dict[str, Any], itinerary_title: str) -> Optional[Dict[str, Any]]:
    user_prompt = build_prompt(stop, itinerary_title)
    print(f"[DEBUG] User Prompt for LLM:\n{user_prompt}") # Verbose log
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[WARN] OPENROUTER_API_KEY not set; skipping")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Cloneable Solver Tags",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "temperature": 0.2,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        print(f"[DEBUG] LLM Raw Response Status: {resp.status_code}") # Verbose log
        print(f"[DEBUG] LLM Raw Response Body:\n{json.dumps(resp.json(), indent=2)}") # Verbose log
        if resp.status_code != 200:
            print(f"[WARN] OpenRouter {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]
        parsed = SolverTags.model_validate_json(raw)
        print(f"[DEBUG] LLM Parsed Tags: {parsed.model_dump()}") # Verbose log
        return parsed.model_dump()
    except Exception as e:
        print(f"[WARN] LLM classification failed for {stop.get('place_name')}: {e}")
        return None


def enrich_stops(stops: List[Dict[str, Any]], itinerary_title: str, force: bool) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for stop in stops:
        if not isinstance(stop, dict):
            enriched.append(stop)
            continue

        if stop.get("solver_data") and not force:
            print(f"[INFO] Skipping stop '{stop.get('place_name', 'Unknown')}' - solver_data exists and force is false.") # Verbose log
            enriched.append(stop)
            continue

        tags = generate_solver_tags(stop, itinerary_title)
        if tags:
            stop = {**stop, "solver_data": tags}
        enriched.append(stop)
        time.sleep(0.2)  # light throttle
    return enriched


def enrich_simple_stops(stops: List[Dict[str, Any]], itinerary_title: str = "Itinerary", force: bool = False) -> List[Dict[str, Any]]:
    """
    Convenience helper for an in-memory list of stop dicts like:
    [
      {"place_name": "...", "notes": "...", "category": "..."},
      ...
    ]
    Adds solver_data to each stop. Does not touch Supabase.
    """
    return enrich_stops(stops, itinerary_title, force)


def main():
    parser = argparse.ArgumentParser(description="Enrich Supabase rows with solver tags.")
    parser.add_argument("--limit", type=int, default=100, help="Rows to process (batch size)")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination (start row)")
    parser.add_argument("--force", action="store_true", help="Recompute even if solver_data exists")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Supabase")
    parser.add_argument("--table", type=str, default="lemon8_articles", help="Supabase table name") # Changed default
    parser.add_argument("--stops-field", type=str, default="itinerary_data", help="Column containing stops array") # Changed default
    parser.add_argument("--pk-field", type=str, default="url", help="Primary key column to update against (defaults to url for lemon8_articles)") # Changed default
    parser.add_argument("--title-field", type=str, default="title", help="Title column (blank to skip)")
    parser.add_argument("--subtitle-field", type=str, default="subtitle", help="Subtitle column (blank to skip)")
    parser.add_argument("--output-field", type=str, default="enriched_itinerary_data", help="Column to write enriched stops to (defaults to stops-field)") # Changed default
    parser.add_argument("--url", type=str, help="Process only a specific article URL") # Added --url argument
    parser.add_argument("--city", type=str, help="Process only articles for a specific city (based on itinerary_data->>city)") # Added --city argument
    args = parser.parse_args()

    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is required.")

    supabase = get_supabase_client()
    if not supabase:
        raise SystemExit("Supabase client not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")

    print(f"[INFO] Fetching up to {args.limit} rows from {args.table} (offset {args.offset})…")
    
    select_cols = [args.pk_field, args.stops_field]
    # Only include title/subtitle fields in select_cols if table is not lemon8_articles
    if args.table != "lemon8_articles":
        if args.title_field and args.title_field.lower() != "none":
            select_cols.append(args.title_field)
        if args.subtitle_field and args.subtitle_field.lower() != "none":
            select_cols.append(args.subtitle_field)

    query = supabase.table(args.table).select(",".join(select_cols))
    
    if args.url:
        query = query.eq(args.pk_field, args.url)
    
    if args.city:
        # For JSONB column, we use ->> operator to extract text and then filter
        query = query.eq(f"{args.stops_field}->>city", args.city)


    res = (
        query
        .order(args.pk_field, desc=False)
        .range(args.offset, args.offset + args.limit - 1)
        .execute()
    )
    rows = res.data or []
    print(f"[INFO] Retrieved {len(rows)} rows")

    for row in rows:
        print(f"\n[DEBUG] Processing row with PK '{row.get(args.pk_field)}':\n{json.dumps(row, indent=2)}") # Verbose log

        stops_raw = row.get(args.stops_field) or []

        stops_key = None
        if isinstance(stops_raw, dict):
            if "stops" in stops_raw:
                stops_key = "stops"
            elif "itinerary" in stops_raw:
                stops_key = "itinerary"

        if stops_key:
            stops = stops_raw.get(stops_key) or []
        else:
            stops = stops_raw
        print(f"[DEBUG] Parsed stops_raw:\n{json.dumps(stops_raw, indent=2)}") # Verbose log
        print(f"[DEBUG] Extracted stops:\n{json.dumps(stops, indent=2)}") # Verbose log

        title = "Itinerary" # Default title
        # If processing lemon8_articles, extract title from enriched_itinerary_data
        if args.table == "lemon8_articles" and isinstance(stops_raw, dict):
            title = stops_raw.get("itinerary_title") or title
        elif args.title_field and args.title_field.lower() != "none":
            title = row.get("new_title") or row.get(args.title_field) or title
        print(f"[DEBUG] Itinerary Title for LLM: {title}") # Verbose log

        updated_stops = enrich_stops(stops, title, force=args.force)
        print(f"[DEBUG] Updated stops after enrichment:\n{json.dumps(updated_stops, indent=2)}") # Verbose log

        if args.dry_run:
            print(f"\n[DRY RUN] {row.get('id') or row.get('source_id')} — first stop solver_data:")
            if updated_stops and isinstance(updated_stops[0], dict):
                print(updated_stops[0].get("solver_data"))
            continue

        pk_field = args.pk_field
        pk_value = row.get(pk_field)
        print(f"[INFO] Updating {pk_field}={pk_value}")
        try:
            target_field = args.output_field or args.stops_field

            if isinstance(stops_raw, dict) and stops_key:
                new_value = {**stops_raw, stops_key: updated_stops}
            elif isinstance(stops_raw, dict):
                new_value = {**stops_raw}
            else:
                new_value = updated_stops
            print(f"[DEBUG] New value for {target_field}:\n{json.dumps(new_value, indent=2)}") # Verbose log

            payload = {target_field: new_value}
            print(f"[DEBUG] Supabase Update Payload:\n{json.dumps(payload, indent=2)}") # Verbose log

            supabase.table(args.table).update({target_field: new_value}).eq(pk_field, pk_value).execute()
        except Exception as e:
            print(f"[WARN] Failed to update {pk_value}: {e}")

    print("[DONE] Enrichment pass complete.")


if __name__ == "__main__":
  main()
