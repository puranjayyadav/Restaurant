import os
import json
import requests
import time
from typing import List, Dict, Any
from supabase import create_client
from decouple import config

# Configuration
SUPABASE_URL = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
SUPABASE_KEY = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))
OPENROUTER_API_KEY = config("OPENROUTER_API_KEY", default=os.getenv("OPENROUTER_API_KEY"))

# LLM Model
MODEL_NAME = "kwaipilot/kat-coder-pro:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize Supabase
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("❌ Supabase credentials missing!")
    exit(1)

if not OPENROUTER_API_KEY:
    print("❌ OpenRouter API Key missing! Set OPENROUTER_API_KEY in .env")
    exit(1)

def get_venues_to_analyze(limit: int = 10):
    """
    Fetch venues that need analysis.
    Criteria:
    - Have reviews in 'reviews' table.
    - do NOT have an entry in 'place_insights' OR entry is old (optional).
    """
    print(f"🔍 Finding venues to analyze (limit={limit})...")
    
    # Simple approach: Get all venues, then check which are missing in place_insights
    # Optimization: In a real large DB, use a join or 'not.in' filter.
    # For now, we'll fetch a batch of venues and check.
    
    # 1. Get IDs already analyzed
    already_analyzed = []
    try:
        res = supabase.table("place_insights").select("place_id").execute()
        already_analyzed = [item['place_id'] for item in res.data]
    except Exception as e:
        print(f"   (Table place_insights might not exist yet or is empty: {e})")

    # 2. Get venues with reviews
    # We want venues that have verified reviews.
    query = supabase.table("venues").select("place_id, name, scraped_review_count").gt("scraped_review_count", 0)
    
    if already_analyzed:
        # Client-side filtering if 'not.in' is tricky with large lists, 
        # but for small batches 'not.in' is fine.
        # string format for filter: (id1,id2,...)
        # query = query.not_.in_("place_id", already_analyzed) # Syntax depends on library version
        pass 

    res = query.limit(limit * 5).execute() # Fetch more to filter client side
    
    candidates = []
    for venue in res.data:
        if venue['place_id'] not in already_analyzed:
            candidates.append(venue)
            if len(candidates) >= limit:
                break
    
    return candidates

def get_reviews_for_venue(place_id: str, limit: int = 20) -> List[str]:
    """Fetch text reviews for a venue."""
    res = supabase.table("reviews").select("text").eq("place_id", place_id).limit(limit).execute()
    return [r['text'] for r in res.data if r.get('text')]

def generate_prompt(place_name: str, reviews: List[str]) -> str:
    reviews_text = "\n".join([f"- {r}" for r in reviews])
    
    return f"""
**Role:** You are the Lead Travel Editor and Data Analyst for "Plandit," a Gen Z itinerary app. Your goal is to convert raw, unstructured reviews into a structured "Insider Intelligence" profile.

**Input Data:**
* **Place Name:** {place_name}
* **Reviews:**
{reviews_text}

**Instructions:**
Analyze the input data and output a single JSON object containing three distinct sections: `display_header`, `insider_profile`, and `plandit_benchmarks`. Follow the specific rules for each section below.

---

### Section 1: Display Header
**Goal:** Create a punchy, 40-char string for the itinerary timeline view.
1.  **Shorten the Name:** Strip corporate fluff (Inc, LLC, generic location tags). Keep it recognizable (e.g., "Starbucks Reserve Roastery" -> "Starbucks Reserve").
2.  **Generate Vibe Hook:** Analyze reviews for a unique, playful selling point.
    * Max 3-4 words.
    * **Must** end with a single relevant emoji.
    * Tone: Exciting, insider-y, playful (e.g., "Flavor Bomb 💣", "Subway Shock 😲", "Cronut Goals 🥐").
3.  **Format:** Combine them as: `"[Short Name]: [Hook]"`

---

### Section 2: Insider Profile
**Goal:** Extract "Social Currency" details for the place detail view.
1.  **must_order:** List 1-3 specific menu items mentioned positively by multiple people (e.g., "Truffle Fries", not "Fries"). Return `[]` if none.
2.  **vibe_tags:** List exactly 3 adjectives describing the atmosphere (e.g., "Intimate", "Chaotic", "Industrial").
3.  **insider_tidbit:** Extract ONE specific tip (e.g., "Sit at the bar for faster service", "Entrance is hidden behind the bookshelf").
4.  **ideal_occasion:** Best use-case (e.g., "First Date", "Quick Solo Lunch", "Group Dinner").
5.  **warning_label:** Any consistent logistical complaints (e.g., "Cash Only", "Long wait times", "Tiny portions"). Return `null` if none.

---

### Section 3: Plandit Benchmarks
**Goal:** specific binary/categorical flags based on keyword logic.
1.  **is_trap:** Boolean. True if reviews suggest it's "overhyped", "tourist trap", or "viral flop".
2.  **grandma_approval:** Boolean. True if sentiment suggests "authentic", "real deal", "traditional", or "reminds me of home".
3.  **work_friendly:** Boolean. True ONLY if reviews explicitly mention good "wifi", "outlets", or "laptops".
4.  **noise_level:** Categorize as "Quiet", "Moderate", or "Loud" (Look for: "can't hear", "shouting", "loud music").
5.  **date_night_score:** Boolean. True if keywords like "romantic", "dim", "candlelit", "intimate" appear.
6.  **safety_flag:** Boolean. True **ONLY** if there are mentions of severe hygiene issues (pests, food poisoning) or harassment.

---

**Output Format:**
Return **ONLY** a valid JSON object. Do not include markdown formatting (like ```json).

{{
  "display_header": {{
    "full_string": "ShortName: Hook Emoji",
    "short_name": "ShortName",
    "hook": "Hook Emoji"
  }},
  "insider_profile": {{
    "must_order": ["Item 1", "Item 2"],
    "vibe_tags": ["Tag1", "Tag2", "Tag3"],
    "insider_tidbit": "String...",
    "ideal_occasion": "String...",
    "warning_label": "String or null"
  }},
  "plandit_benchmarks": {{
    "is_trap": boolean,
    "grandma_approval": boolean,
    "work_friendly": boolean,
    "noise_level": "String",
    "date_night_score": boolean,
    "safety_flag": boolean
  }}
}}
"""

def call_llm(place_name: str, reviews: List[str]) -> Dict[str, Any]:
    prompt = generate_prompt(place_name, reviews)
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://plandit.app", # Optional, for OpenRouter rankings
        "X-Title": "Plandit Scraper", # Optional
    }
    
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    print(f"   🤖 Sending request to {MODEL_NAME}...")
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result_json = response.json()
        content = result_json['choices'][0]['message']['content']
        
        # Clean up markdown if present
        content = content.replace("```json", "").replace("```", "").strip()
        
        return json.loads(content)
        
    except Exception as e:
        print(f"   ❌ LLM Error: {e}")
        if response:
             print(f"   Response: {response.text}")
        return None

def save_insight_to_supabase(place_id: str, llm_output: Dict[str, Any]):
    print(f"   💾 Saving insights for {place_id}...")
    
    data_to_insert = {
        "place_id": place_id,
        "display_short_name": llm_output["display_header"]["short_name"],
        "display_hook": llm_output["display_header"]["hook"],
        "is_trap": llm_output["plandit_benchmarks"]["is_trap"],
        "work_friendly": llm_output["plandit_benchmarks"]["work_friendly"],
        "safety_flag": llm_output["plandit_benchmarks"]["safety_flag"],
        "full_ai_json": llm_output,
        "last_analyzed_at": "now()"
    }
    
    try:
        supabase.table("place_insights").upsert(data_to_insert, on_conflict="place_id").execute()
        print("   ✅ Saved successfully.")
    except Exception as e:
        print(f"   ❌ DB Error: {e}")

def main():
    print(f"🚀 Starting Place Insights Generator using {MODEL_NAME}")
    
    import sys
    # Default limit
    limit = 10
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("⚠️ Invalid limit argument, using default 10.")

    venues = get_venues_to_analyze(limit=limit)
    
    if not venues:
        print("✅ No venues needing analysis found.")
        return

    print(f"🎯 Found {len(venues)} venues to process.")
    
    for i, venue in enumerate(venues):
        place_id = venue['place_id']
        place_name = venue['name']
        print(f"\n[{i+1}/{len(venues)}] Processing: {place_name} ({place_id})")
        
        reviews = get_reviews_for_venue(place_id)
        if not reviews:
            print("   ⚠️ No reviews found, skipping.")
            continue
            
        print(f"   Fetched {len(reviews)} reviews.")
        
        if len(reviews) < 3:
             print("   ⚠️ Too few reviews for reliable insights, skipping.")
             # optional: continue
        
        insights = call_llm(place_name, reviews)
        
        if insights:
            save_insight_to_supabase(place_id, insights)
            
        # Rate limit friendly
        time.sleep(2)

if __name__ == "__main__":
    main()
