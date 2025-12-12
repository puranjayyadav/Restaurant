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
        if resp.status_code != 200:
            print(f"[WARN] OpenRouter {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]
        parsed = SolverTags.model_validate_json(raw)
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
    parser = argparse.ArgumentParser(description="Enrich cloneable_adventures stops with solver tags.")
    parser.add_argument("--limit", type=int, default=100, help="Rows to process (batch size)")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination (start row)")
    parser.add_argument("--force", action="store_true", help="Recompute even if solver_data exists")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Supabase")
    parser.add_argument("--table", type=str, default="cloneable_adventures", help="Supabase table name")
    parser.add_argument("--stops-field", type=str, default="stops", help="Column containing stops array")
    parser.add_argument("--pk-field", type=str, default="source_id", help="Primary key column to update against")
    parser.add_argument("--title-field", type=str, default="title", help="Title column (blank to skip)")
    parser.add_argument("--subtitle-field", type=str, default="subtitle", help="Subtitle column (blank to skip)")
    parser.add_argument("--output-field", type=str, default=None, help="Column to write enriched stops to (defaults to stops-field)")
    args = parser.parse_args()

    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is required.")

    supabase = get_supabase_client()
    if not supabase:
        raise SystemExit("Supabase client not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")

    print(f"[INFO] Fetching up to {args.limit} rows from {args.table} (offset {args.offset})…")
    select_cols = [args.pk_field, args.stops_field]
    if args.title_field and args.title_field.lower() != "none":
        select_cols.append(args.title_field)
    # Keep new_title if present; harmless if missing because PostgREST ignores unknown selects? It raises error.
    # To be safe, only include if user explicitly sets it.
    # We'll include subtitle_field similarly.
    if args.subtitle_field and args.subtitle_field.lower() != "none":
        select_cols.append(args.subtitle_field)
    res = (
        supabase.table(args.table)
        .select(",".join(select_cols))
        .order(args.pk_field, desc=False)
        .range(args.offset, args.offset + args.limit - 1)
        .execute()
    )
    rows = res.data or []
    print(f"[INFO] Retrieved {len(rows)} rows")

    for row in rows:
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

        title_source = None
        if args.title_field and args.title_field.lower() != "none":
            title_source = row.get(args.title_field)
        title = row.get("new_title") or title_source or "Itinerary"
        updated_stops = enrich_stops(stops, title, force=args.force)

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

            supabase.table(args.table).update({target_field: new_value}).eq(pk_field, pk_value).execute()
        except Exception as e:
            print(f"[WARN] Failed to update {pk_value}: {e}")

    print("[DONE] Enrichment pass complete.")


if __name__ == "__main__":
  main()

