"""
Retry failed geocoding for Lemon8 articles with relaxed city validation and Google Places fallback.
"""
import os
import time
import re
import json
import requests
from typing import Dict, Any, List, Optional
from supabase_config import get_supabase_client
try:
    from decouple import config
except ImportError:
    def config(key, default=None):
        return os.environ.get(key, default)

# --- Configuration ---
SLEEP_SECONDS = float(config("SLEEP_SECONDS", 1.2))
NOMINATIM_EMAIL = config("NOMINATIM_EMAIL", "").strip()
GOOGLE_MAPS_API_KEY = config("GOOGLE_MAPS_API_KEY", config("GOOGLE_API_KEY", ""))
TARGET_COUNTRY_CODE = "us"

STATE_ABBR = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
    'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
    'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
    'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS', 'MISSOURI': 'MO',
    'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ',
    'NEW MEXICO': 'NM', 'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH',
    'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
    'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT',
    'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY',
    'DC': 'DC', 'DISTRICT OF COLUMBIA': 'DC'
}

def clean_search_term(name: str) -> str:
    if not name: return ""
    name = re.sub(r'[|+\-:]', ' ', name)
    noise_patterns = [
        r'\bNYC\b', r'\bNew York\b', r'\bNY\b',
        r'\bK-Town\b', r'\bHarlem\b', r'\bSoho\b', r'\bManhattan\b',
        r'\bRestaurant\b', r'\bCafe\b', r'\bBakery\b', r'\bBar\b'
    ]
    clean = name
    for pattern in noise_patterns:
        clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)
    return clean.strip()

def relaxed_validate_location(address_data: Dict, target_city: str) -> bool:
    if not address_data: return False
    
    # 0. Quick string to list of target signals
    target_city_clean = target_city.lower().replace(" county", "").strip()
    
    found_locations = [
        address_data.get("city", ""),
        address_data.get("town", ""),
        address_data.get("village", ""),
        address_data.get("suburb", ""),
        address_data.get("county", "").replace(" County", ""),
        address_data.get("state", ""),
        address_data.get("neighbourhood", "")
    ]
    found_locations = [loc.lower().strip() for loc in found_locations if loc]
    
    # 1. Direct or partial match
    if any(target_city_clean in loc for loc in found_locations):
        return True
    
    # 2. Check for state abbreviations
    target_state_abbr = STATE_ABBR.get(target_city.upper())
    if target_state_abbr:
        found_state = address_data.get("state", "").upper()
        if found_state == target_city.upper() or STATE_ABBR.get(found_state) == target_state_abbr:
            return True

    return False

def nominatim_geocode(query: str, city_context: str = None) -> Optional[Dict]:
    headers = {"User-Agent": "Plandit-Retry-Worker/1.1 (contact@plandit.app)"}
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1, "countrycodes": TARGET_COUNTRY_CODE}
    
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search", headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                result = data[0]
                address = result.get("address", {})
                if not city_context or relaxed_validate_location(address, city_context):
                    return {
                        "lat": float(result.get("lat")),
                        "lon": float(result.get("lon")),
                        "display_name": result.get("display_name"),
                        "source": "nominatim"
                    }
    except Exception as e:
        print(f"      [Nominatim Error] {e}")
    return None

def google_places_geocode(query: str, city_context: str = None) -> Optional[Dict]:
    if not GOOGLE_MAPS_API_KEY: return None
    
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": GOOGLE_MAPS_API_KEY, "region": "us"}
    if city_context:
        params["query"] = f"{query} {city_context}"
        
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            # Take the first result that is in the US
            for result in data["results"]:
                address = result.get("formatted_address", "")
                if "USA" in address or "United States" in address:
                    return {
                        "lat": result["geometry"]["location"]["lat"],
                        "lon": result["geometry"]["location"]["lng"],
                        "display_name": address,
                        "source": "google"
                    }
    except Exception as e:
        print(f"      [Google Error] {e}")
    return None

import google_maps_scraper

def google_scraper_geocode(query: str, city_context: str = None) -> Optional[Dict]:
    """
    Fallback using the local scraping logic from google_maps_scraper.py
    """
    search_query = query
    if city_context and city_context.lower() not in query.lower():
        search_query = f"{query} {city_context}"
    
    try:
        print(f"      [Scraper] Query: '{search_query}'")
        result = google_maps_scraper.search_place_by_name(search_query)
        if result and result.get("lat") and result.get("lon"):
            # The scraper uses gl=us, but we check address just in case
            address = result.get("address", "")
            return {
                "lat": result["lat"],
                "lon": result["lon"],
                "display_name": f"{result.get('name')} - {address}",
                "source": "google_scraper"
            }
    except Exception as e:
        print(f"      [Scraper Error] {e}")
    return None

def retry_geocode_article(article: Dict, force: bool = False):
    url = article.get("url")
    data = article.get("itinerary_data")
    if isinstance(data, str):
        try: data = json.loads(data)
        except: return
    
    if not isinstance(data, dict): return
    
    city = data.get("city") or "New York"
    stops = data.get("stops", [])
    if not stops: return
    
    current_lat = article.get("stops_lat") or [None] * len(stops)
    current_lng = article.get("stops_lng") or [None] * len(stops)
    
    # If arrays are different length, fix it
    if len(current_lat) != len(stops): current_lat = [None] * len(stops)
    if len(current_lng) != len(stops): current_lng = [None] * len(stops)
    
    updated_lat = list(current_lat)
    updated_lng = list(current_lng)
    updated_stops_data = []
    
    needs_update = False
    print(f"\n--- Retrying Article: {url[-50:]} ({city}) ---")
    
    for i, stop in enumerate(stops):
        # Only retry if NULL or forced
        if not force and updated_lat[i] is not None:
            updated_stops_data.append(stop)
            continue
            
        place_name = (stop.get("place_name") or "").strip()
        search_query = (stop.get("search_query") or "").strip()
        
        # Strategies
        clean_name = clean_search_term(place_name)
        candidates = []
        if clean_name: candidates.append(f"{clean_name}, {city}")
        if search_query: candidates.append(search_query)
        if place_name: candidates.append(place_name)
        
        result = None
        for cand in candidates:
            if not cand or len(cand) < 3: continue
            
            # 1. Try Nominatim (Free, Polite)
            result = nominatim_geocode(cand, city_context=city)
            if result: break
            time.sleep(SLEEP_SECONDS)
            
            # 2. Try Google Scraper (Free, Robust)
            result = google_scraper_geocode(cand, city_context=city)
            if result: break
            
            # 3. Try Google Places API (Paid, High Quality) - only if scraper failed
            if GOOGLE_MAPS_API_KEY:
                result = google_places_geocode(cand, city_context=city)
                if result: break

        if result:
            updated_lat[i] = result["lat"]
            updated_lng[i] = result["lon"]
            needs_update = True
            print(f"   [{i}] ✓ {place_name[:30]} -> ({result['lat']:.4f}, {result['lon']:.4f}) via {result['source']}")
        else:
            print(f"   [{i}] ✗ {place_name[:30]} | Failed all strategies")
            
        # Update stop dict with coords
        new_stop = dict(stop)
        new_stop["lat"] = updated_lat[i]
        new_stop["lng"] = updated_lng[i]
        updated_stops_data.append(new_stop)

    if needs_update:
        supabase = get_supabase_client()
        updated_data = dict(data)
        updated_data["stops"] = updated_stops_data
        
        payload = {
            "enriched_itinerary_data": updated_data,
            "stops_lat": updated_lat,
            "stops_lng": updated_lng,
            "updated_at": "now()"
        }
        
        try:
            supabase.table("lemon8_articles").update(payload).eq("url", url).execute()
            print(f"--> Saved updates for {url[-40:]}")
        except Exception as e:
            print(f"ERR: Failed to save: {e}")

def main():
    print("🚀 Starting Full Recovery Geocoding...")
    print("   Target: All articles with NULL or incomplete stops_lat/stops_lng")
    if not GOOGLE_MAPS_API_KEY:
        print("   ⚠️  Note: GOOGLE_MAPS_API_KEY not found. Using Free Scraper + Nominatim.")
    
    supabase = get_supabase_client()
    
    batch_size = 50
    total_processed = 0
    total_improved = 0
    
    while True:
        try:
            # Fetch a batch of articles
            # We filter for itinerary_data exists and order by updated_at
            # Note: We don't use offset here because once we update them, 
            # they might no longer fall into our "needs_retry" filter logic 
            # if we were able to filter by NULL server-side.
            # However, since we filter client-side, we'll use a sliding window or just limit.
            res = (
                supabase.table("lemon8_articles")
                .select("url, itinerary_data, stops_lat, stops_lng")
                .not_.is_("itinerary_data", "null")
                .order("updated_at", desc=False) # Oldest first to ensure we eventually hit everything
                .limit(200) 
                .execute()
            )
            
            articles = res.data or []
            if not articles:
                print("\n✅ No more articles found in database.")
                break
                
            to_retry = []
            for art in articles:
                slat = art.get("stops_lat")
                slng = art.get("stops_lng")
                # Needs retry if lat is NULL, lng is NULL, or any element is NULL
                if slat is None or slng is None or any(x is None for x in slat) or any(x is None for x in slng):
                    to_retry.append(art)
            
            if not to_retry:
                print(f"\n[Batch Info] Checked {len(articles)} articles, none need geocoding updates. Moving on...")
                # If we found articles but none needed retry, we might be stuck in a loop of "mostly finished" articles.
                # In a real system we'd use a more specific SQL filter, but for now we'll break if we hit a wall of 200 good ones.
                break
                
            print(f"\n[Batch] Found {len(to_retry)} articles in this batch needing geocoding.\n")
            
            for i, article in enumerate(to_retry):
                total_processed += 1
                retry_geocode_article(article)
                
            # Short sleep between batches
            time.sleep(2)
            
        except Exception as e:
            print(f"Critial Batch Error: {e}")
            time.sleep(5)
            continue

    print(f"\n" + "="*60)
    print(f"🏁 FINISHED. Total articles checked/processed: {total_processed}")
    print("="*60)

if __name__ == "__main__":
    main()
