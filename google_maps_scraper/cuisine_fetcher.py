"""
Google Maps Scraper - Cuisine Fetcher
A standalone scraper for extracting place data from Google Maps.
Includes optional Google Places API integration for accurate viewports
and multi-threaded grid searching.
"""

import json
import time
import urllib.parse
import os
import math
import random
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple, Set

# Try to import requests
try:
    import requests
except ImportError:
    print("Error: 'requests' library is missing. Please run: pip install requests")
    exit(1)

# Try to import Supabase storage (optional)
try:
    from supabase_storage import save_batch_to_supabase, supabase
    SUPABASE_ENABLED = supabase is not None
    if SUPABASE_ENABLED:
        print("Supabase integration enabled")
except ImportError:
    SUPABASE_ENABLED = False
    print("Supabase integration not available (install: pip install supabase python-decouple)")

# Configuration
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")  # Optional: Set in your env vars


def prepare_data(input_data: str) -> List[Any]:
    """Prepares the raw response data for parsing."""
    try:
        cleaned = input_data
        if len(cleaned) >= 6 and cleaned.endswith('/*""*/'):
            cleaned = cleaned[:len(cleaned) - 6]
        
        # Try standard JSON parse
        try:
            decoder = json.JSONDecoder()
            outer_json, _ = decoder.raw_decode(cleaned)
        except (json.JSONDecodeError, ValueError):
            # Try removing prefix
            if ")]}'" in cleaned:
                cleaned = cleaned.split(")]}'")[1].strip()
                try:
                    decoder = json.JSONDecoder()
                    outer_json, _ = decoder.raw_decode(cleaned)
                except:
                    return []
            else:
                return []
        
        # Handle {"d": ...} format
        if isinstance(outer_json, dict) and 'd' in outer_json:
            d = outer_json['d']
            if isinstance(d, str):
                d = d.replace('\n', '').strip()
                if d.startswith(")]}'"):
                    d = d[4:]
                try:
                    d_parsed = json.loads(d)
                    if isinstance(d_parsed, list) and len(d_parsed) > 0:
                         # Navigate to the specific array containing results
                        if isinstance(d_parsed[0], list) and len(d_parsed[0]) > 1:
                            if isinstance(d_parsed[0][1], list):
                                return [x[14] for x in d_parsed[0][1] if isinstance(x, list) and len(x) > 14]
                except:
                    pass
            elif isinstance(d, list):
                 if len(d) > 0 and isinstance(d[0], list) and len(d[0]) > 1:
                    if isinstance(d[0][1], list):
                        return [x[14] for x in d[0][1] if isinstance(x, list) and len(x) > 14]

        # Handle direct array format
        try:
            if isinstance(outer_json, list) and len(outer_json) > 0:
                 if isinstance(outer_json[0], list) and len(outer_json[0]) > 1:
                    if isinstance(outer_json[0][1], list):
                        return [x[14] for x in outer_json[0][1] if isinstance(x, list) and len(x) > 14]
        except:
            pass

        return []
    except Exception:
        return []


def prepare_lookup(data: List[Any]):
    """Creates a safe lookup function for nested lists."""
    def lookup(*indexes):
        try:
            result = data
            for idx in indexes:
                result = result[idx]
            return result
        except (IndexError, TypeError, KeyError):
            return None
    return lookup


def get_lat_long(lookup) -> Dict[str, Optional[float]]:
    lat = lookup(208, 0, 2) or lookup(37, 0, 0, 8, 0, 2)
    long = lookup(208, 0, 3) or lookup(37, 0, 0, 8, 0, 1)
    return {'lat': lat, 'long': long}


def get_hours(lookup) -> List[Dict[str, Any]]:
    hours_array = lookup(203, 0)
    if not hours_array:
        return []
    
    hours = []
    for day_data in hours_array:
        if not day_data: continue
        
        try:
            day = day_data[0]
            hours_str = None
            open_24 = None
            close_24 = None
            
            if len(day_data) > 3 and day_data[3]:
                h_data = day_data[3]
                if len(h_data) > 0 and h_data[0]:
                    hours_str = h_data[0][0]
                    if len(h_data[0]) > 1 and h_data[0][1]:
                        open_24 = h_data[0][1][0][0]
                        close_24 = h_data[0][1][1][0]
            
            hours.append({
                'day': day,
                'hours': hours_str,
                'open24Hour': open_24,
                'close24Hour': close_24
            })
        except (IndexError, TypeError):
            pass
    return hours


def find_photo_urls(data: Any, depth: int = 0, max_depth: int = 5, max_photos: int = 10) -> List[str]:
    photos = []
    if depth > max_depth: return photos
    
    if isinstance(data, str):
        if (('googleusercontent' in data or 'maps.googleapis.com' in data or 'streetview' in data) and 
            not any(x in data for x in ['logo', 'icon', 'default_user', 'avatar'])):
            photos.append(data.strip())
    
    elif isinstance(data, list):
        for item in data:
            if len(photos) >= max_photos: break
            photos.extend(find_photo_urls(item, depth + 1, max_depth, max_photos))
    
    elif isinstance(data, dict):
        for value in data.values():
            if len(photos) >= max_photos: break
            photos.extend(find_photo_urls(value, depth + 1, max_depth, max_photos))
            
    return photos


def build_results(prepared_data: List[Any]) -> List[Dict[str, Any]]:
    results = []
    for place in prepared_data:
        if not place: continue
        lookup = prepare_lookup(place)
        
        website = lookup(7, 0)
        if website: website = website.replace('/url', '').split('?')[0]
        
        name = lookup(11)
        if not name: continue
        
        # Photo Extraction
        photos = []
        known_indices = [6, 7, 8, 9, 10, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35]
        for idx in known_indices:
            p_data = lookup(idx)
            if p_data:
                photos.extend(find_photo_urls(p_data))
                if len(photos) >= 10: break
        
        # Fallback photo search
        if not photos:
            for idx in range(min(len(place), 200)):
                p_data = lookup(idx)
                if p_data:
                    photos.extend(find_photo_urls(p_data))
                    if len(photos) >= 10: break

        unique_photos = list(dict.fromkeys(photos))[:8]
        photo_objects = [{'url': u, 'photo_url': u} for u in unique_photos]
        
        coords = get_lat_long(lookup)
        
        full_addr = f"{lookup(183, 1, 2) or ''} {lookup(183, 1, 3) or ''} {lookup(183, 1, 5) or ''} {lookup(183, 1, 4) or ''}"
        
        # Extract FID (Feature ID) - used for detailed lookups
        fid = lookup(10)
        
        results.append({
            'name': name,
            'full_address': full_addr.strip(),
            'street_address': lookup(183, 1, 2),
            'city': lookup(183, 1, 3),
            'state': lookup(183, 1, 5),
            'zip': lookup(183, 1, 4),
            'website': website or '',
            'phone': lookup(178, 0, 0),
            'avg_rating': lookup(4, 7),
            'total_reviews': lookup(4, 8),
            'place_id': lookup(78),
            'lat': coords['lat'],
            'long': coords['long'],
            'hours': get_hours(lookup),
            'photos': photo_objects
        })
    return results


def google_maps_api_text_search(query: str) -> Optional[Dict[str, Any]]:
    """
    Uses the official Google Places API to get viewport data.
    Only runs if GOOGLE_MAPS_API_KEY is present.
    """
    if not GOOGLE_MAPS_API_KEY:
        return None
        
    try:
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={urllib.parse.quote(query)}&key={GOOGLE_MAPS_API_KEY}"
        response = requests.get(url)
        data = response.json()
        if data.get('results'):
            return data['results'][0]
    except Exception as e:
        print(f"API Search Error: {e}")
    return None


def search_place_scraper(place_name: str) -> Optional[Dict[str, Any]]:
    """Fallback: Scrapes basic coordinates if no API key is available."""
    try:
        encoded_query = urllib.parse.quote(place_name)
        # Simplified URL for scraping a single location's center
        url = f"https://www.google.com/search?tbm=map&q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        }
        
        res = requests.get(url, headers=headers)
        if res.status_code != 200: return None
        
        html = res.text
        # Remove protection chars
        if ")]}'" in html:
            html = html.split(")]}'")[1]
        
        # This is a very rough parsing for the fallback. 
        # In a real scenario, you might parse the initial state variable from the HTML.
        # For this script, we rely on the main scraping function.
        # Returning None forces the script to fail gracefully or use hardcoded defaults.
        return None 
    except:
        return None


def get_long_lat_grid(place_viewport: Dict[str, Any], grid_size: int = 5) -> List[Tuple[float, float]]:
    """
    Generates a grid of lat/long coordinates based on a viewport.
    Ported from the Node.js implementation.
    """
    try:
        ne = place_viewport['northeast']
        sw = place_viewport['southwest']
        
        northeast_lat = ne['lat']
        northeast_lng = ne['lng']
        southwest_lat = sw['lat']
        southwest_lng = sw['lng']
    except KeyError:
        return []

    output = []
    epsilon = 0.0000001
    intermediate_grid_length = grid_size - 1
    
    if intermediate_grid_length <= 0:
        return [(southwest_lat, southwest_lng)]

    lat_step_size = (northeast_lat - southwest_lat) / intermediate_grid_length
    lng_step_size = (northeast_lng - southwest_lng) / intermediate_grid_length

    lat = southwest_lat
    while lat <= northeast_lat + epsilon:
        lng = southwest_lng
        while lng <= northeast_lng + epsilon:
            output.append((lat, lng))
            lng += lng_step_size
        lat += lat_step_size
    
    return output


def get_google_maps_data(
    query: str, 
    lat: float, 
    lon: float, 
    zoom: float = 13500, 
    count: int = 200, 
    start: int = 0
) -> List[Dict[str, Any]]:
    """Fetches data for a single grid point."""
    try:
        encoded_query = urllib.parse.quote(query)
        url = (
            f"https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&"
            f"pb=!4m12!1m3!1d{zoom}!2d{lon}!3d{lat}!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!"
            f"7i{count}!8i{start}!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!"
            f"17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!"
            f"6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!"
            f"1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!"
            f"1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!"
            f"24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!"
            f"13b1!14b1!17b1!20b1!21b1!22b1!25b1!27m1!1b0!28b0!31b0!32b0!33m1!1b0!10m1!8e3!11m1!3e1!"
            f"14m1!3b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m2!2i1!3i1!43b1!52b1!"
            f"54m1!1b1!55b1!56m1!1b1!65m5!3m4!1m3!1m2!1i224!2i298!71b1!72m19!1m5!1b1!2b1!3b1!5b1!7b1!4b1!"
            f"8m10!1m6!4m1!1e1!4m1!1e3!4m1!1e4!3sother_user_reviews!6m1!1e1!9b1!89b1!103b1!113b1!114m3!1b1!"
            f"2m1!1b1!117b1!122m1!1b1!125b0!26m4!2m3!1i80!2i92!4i8!30m28!1m6!1m2!1i0!2i0!2m2!1i530!2i376!"
            f"1m6!1m2!1i1870!2i0!2m2!1i1920!2i376!1m6!1m2!1i0!2i0!2m2!1i1920!2i20!1m6!1m2!1i0!2i356!"
            f"2m2!1i1920!2i376!34m18!2b1!3b1!4b1!6b1!8m6!1b1!3b1!4b1!5b1!6b1!7b1!9b1!12b1!14b1!20b1!"
            f"23b1!25b1!26b1!37m1!1e81!42b1!46m1!1e10!47m0!49m8!3b1!6m2!1b1!2b1!7m2!1e3!2b1!8b1!50m34!"
            f"1m29!2m7!1u49!4sIn+stock!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKoGKBc!10m2!50m1!1e1!"
            f"2m7!1u3!4s!5e1!9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKsGKBg!10m2!3m1!1e1!2m7!1u2!4s!5e1!"
            f"9s0ahUKEwjmn8i0ucCGAxVbGtAFHVuHAiwQ_KkBCKwGKBk!10m2!2m1!1e1!3m1!1u2!3m1!1u3!4BIAE!2e2!3m2!1b1!3b1!"
            f"59BQ2dBd0Fn!61b1!67m2!7b1!10b1!69i695&q={encoded_query}&tch=1&ech=3&psi=STleZpLoHLy4wN4Ps-iR2Aw.1717451082784.1"
        )
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.114 Safari/537.36',
        }
        
        # Add a random delay to be polite
        time.sleep(0.5)
        
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            return build_results(prepare_data(response.text))
            
    except Exception as e:
        print(f"Error scraping grid point {lat},{lon}: {e}")
    return []


def run_grid_search(location_name: str, search_query: str, grid_dimension: int = 3) -> List[Dict[str, Any]]:
    """
    Orchestrates the grid search:
    1. Get viewport (API or Fallback)
    2. Generate Grid
    3. Threaded Scrape
    4. Save to JSON
    5. Return results for Supabase storage
    """
    print(f"--- Starting Search for '{search_query}' in '{location_name}' ---")
    
    # 1. Get Viewport
    print("Fetching location details...")
    viewport = None
    place_details = google_maps_api_text_search(location_name)
    
    if place_details and 'geometry' in place_details:
        viewport = place_details['geometry']['viewport']
        print("Using API-provided viewport.")
    else:
        # Check hardcoded neighborhood data
        from neighborhood_data import get_neighborhood_viewport
        viewport = get_neighborhood_viewport(location_name)
        
        if viewport:
            print(f"Using hardcoded viewport for '{location_name.split(',')[0]}'")
        else:
            print("API Key missing and no hardcoded data found. Trying HTML fallback scraper...")
            # Still try the scraper if we don't know the neighborhood
            scraped_data = search_place_scraper(location_name)
        
    if not viewport:
         print("WARNING: Using fallback coordinates (SoHo/Manhattan) as last resort.")
         viewport = {
            'northeast': {'lat': 40.730, 'lng': -73.990},
            'southwest': {'lat': 40.710, 'lng': -74.010}
        }

    # 2. Generate Grid
    grid = get_long_lat_grid(viewport, grid_dimension)
    print(f"Generated grid with {len(grid)} points.")

    # 3. Threaded Scrape
    all_results = []
    
    # Use ThreadPoolExecutor for parallel execution
    # Be careful not to set max_workers too high or Google will block your IP
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for lat, lon in grid:
            futures.append(
                executor.submit(get_google_maps_data, search_query, lat, lon)
            )
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                data = future.result()
                all_results.extend(data)
                print(f"Finished grid point {i+1}/{len(grid)} - Found {len(data)} places")
            except Exception as e:
                print(f"Grid point failed: {e}")

    # 4. Deduplicate (Logic from Node.js script)
    unique_places = {}
    for place in all_results:
        pid = place.get('place_id')
        if pid and pid not in unique_places:
            unique_places[pid] = place
    
    final_results = list(unique_places.values())
    
    # 5. Output to JSON - DISABLED
    print(f"\nSearch Complete. Found {len(final_results)} unique places.")
    
    # filename = f"{location_name.replace(' ', '_')}_{search_query.replace(' ', '_')}.json"
    # with open(filename, 'w', encoding='utf-8') as f:
    #     json.dump(final_results, f, indent=2, ensure_ascii=False)
    # 
    # print(f"Results saved to {filename}")
    
    # 6. Return results for Supabase storage
    return final_results



# --- 2. DEFINE CUISINES ---
CUISINE_LIST = {
    "pizza_nyc": "classic new york slice thin crust coal oven brick oven",
    "jewish_deli": "kosher deli pastrami on rye matzo ball soup bagels lox",
    "chinese_cantonese": "dim sum banquet hall roast duck chinatown classics",
    "chinese_xian": "hand pulled noodles spicy cumin lamb burger western china",
    "chinese_sichuan": "ma la peppercorn mapo tofu spicy fish stew",
    "italian_red_sauce": "italian american chicken parm meatballs sunday gravy arthur avenue",
    "italian_regional": "tuscan sicilian roman pasta authentic regional specialties",
    "dominican": "mofongo chicharron de pollo rice and beans washington heights",
    "puerto_rican": "lechon asado pernil mofongo alcapurrias nuyorican",
    "mexican_street": "tacos al pastor street cart elote cemitas puebla style",
    "korean_bbq": "k-town table grilling galbi bulgogi banchan soju",
    "korean_pocha": "korean comfort food army stew fried chicken late night",
    "japanese_sushi": "omakase edomae sushi hand rolls fresh fish tsukiji market style",
    "japanese_izakaya": "yakitori skewers ramen small plates sake bar",
    "thai_isan": "northeast thai spicy papaya salad larb grilled pork",
    "vietnamese": "pho beef noodle soup banh mi sandwiches vietnamese coffee",
    "indian_north": "butter chicken naan tandoori mughlai creamy curries",
    "indian_south": "dosa idli sambar vegetarian spicy chettinad",
    "halal_cart": "chicken over rice lamb gyro white sauce hot sauce street food",
    "soul_food": "fried chicken mac and cheese collard greens cornbread harlem staple",
    "caribbean_jamaican": "jerk chicken oxtail stew curry goat patties",
    "greek_taverna": "grilled whole fish octopus feta salad astoria seafood",
    "middle_eastern": "falafel hummus shawarma lebanese syrian palestinian",
    "eastern_european": "pierogi borscht blini ukrainian diner polish milk bar",
    "russian": "caviar vodka infused stroganoff little odessa brighton beach",
    "french_bistro": "steak frites onion soup escargots croque monsieur brasserie",
    "uzbek": "hand pulled lagman noodles plov lamb samsa central asian",
    "ethiopian": "injera bread tibs wat communal dining vegetarian platter",
    "senegalese": "thieboudienne jollof rice yassa chicken west african",
    "colombian": "arepas bandeja paisa sancocho empanadas jackson heights",
    "peruvian": "ceviche lomo saltado pisco sour rotisserie chicken polla a la brasa",
    "new_american": "farm to table seasonal market driven small plates fusion",
    "australian_cafe": "brekkie avocado smash flat white ricotta hotcakes"
}

# --- 2.5 DEFINE AESTHETIC MODIFIERS ---
AESTHETIC_MODIFIERS = [
    "instagrammable",
    "trendy",
    "beautiful interior",
    "viral",
    "cute",
    "chic",
    "photogenic"
]


def generate_aesthetic_queries(neighborhood: str, cuisine_term: str) -> List[str]:
    """Builds aesthetic-focused queries for a cuisine in a neighborhood."""
    return [
        f"Trendy {cuisine_term} restaurants in {neighborhood}",
        f"Most {AESTHETIC_MODIFIERS[0]} {cuisine_term} in {neighborhood}",
        f"{cuisine_term} with {AESTHETIC_MODIFIERS[2]} in {neighborhood}"
    ]


# --- 3. DEFINE NEIGHBORHOODS ---
NYC_AREAS = {
    # === BATCH 1: MANHATTAN SOUTH (Downtown & Nightlife) ===
    "Manhattan_South": [
        "Financial District", "Tribeca", "SoHo", "Little Italy", 
        "Chinatown", "Lower East Side", "East Village", 
        "West Village", "Greenwich Village", "Nolita"
    ],

    # === BATCH 2: MANHATTAN MID (Business & Koreatown) ===
    "Manhattan_Mid": [
        "Chelsea", "Meatpacking District", "Flatiron District", 
        "Gramercy Park", "Midtown West", "Hell's Kitchen", 
        "Koreatown", "Murray Hill", "NoMad"
    ],

    # === BATCH 3: MANHATTAN NORTH (Classic NY & Soul Food) ===
    # *CRITICAL ADDITION* for Soul Food, Harlem Classics, and High-End Dining
    "Manhattan_North": [
        "Upper West Side", "Upper East Side", "Harlem", 
        "East Harlem", "Morningside Heights"
    ],

    # === BATCH 4: BROOKLYN HOTSPOTS (Trendy & Hip) ===
    "Brooklyn_Hotspots": [
        "Williamsburg", "Greenpoint", "DUMBO", "Brooklyn Heights", 
        "Cobble Hill", "Bushwick", "Bed-Stuy", "Fort Greene", "Prospect Heights"
    ],
    
    # === BATCH 5: QUEENS HOTSPOTS (The "Global Kitchen") ===
    "Queens_Hotspots": [
        "Long Island City", "Astoria", "Sunnyside", 
        "Jackson Heights", "Flushing", "Elmhurst", "Woodside"
    ],

    # === BATCH 6: SPECIALTY ZONES (Specific Cuisines) ===
    # Use these for specific cuisine hunts that don't fit the "hotspot" vibe
    "Specialty_Zones": [
        "Arthur Avenue", # The Bronx (Real Italian)
        "Brighton Beach", # South Brooklyn (Russian/Ukrainian)
        "Sunset Park" # Brooklyn (Chinatown #3 & Mexican)
    ]
}

if __name__ == "__main__":
    import time
    import random

    # --- 1. SETTINGS ---
    GRID_SIZE = 2

    print("--- Starting Full Run (All Neighborhoods) ---")

    # Outer Loop: Area Groups
    for area_group, neighborhoods in NYC_AREAS.items():
        print(f"\n=== STARTING BATCH: {area_group} ===")
        
        # PRO TIP: Shuffle the list so you don't always scrape in the exact same alphabetical order.
        # This helps avoid bot detection patterns.
        random.shuffle(neighborhoods) 

        # Middle Loop: Specific Neighborhoods
        for hood in neighborhoods:
            location_string = f"{hood}, New York, NY"
            print(f"\n>> Moving to neighborhood: {hood}")
            
            # Inner Loop: Cuisines
            for cuisine_name, search_query in CUISINE_LIST.items():
                print(f"   > Searching for '{cuisine_name}'...")
                
                # 1. Run the search
                try:
                    results = run_grid_search(location_string, search_query, GRID_SIZE)
                    
                    # 2. Sync to Supabase if enabled
                    if SUPABASE_ENABLED and results:
                        neighborhood_name = hood.split(',')[0].strip()
                        save_batch_to_supabase(results, cuisine_name, neighborhood_name)
                except Exception as e:
                    print(f"   [!] Error searching {cuisine_name} in {hood}: {e}")
                    # Continue to next cuisine even if this one fails
                    continue 

                # 2. Variable Sleep (5-12 seconds)
                sleep_seconds = random.uniform(5, 12)
                print(f"   [Waiting {sleep_seconds:.1f}s...]")
                time.sleep(sleep_seconds)

                # 3. Aesthetic pass for the same cuisine
                aesthetic_queries = generate_aesthetic_queries(hood, search_query)
                for aesthetic_query in aesthetic_queries:
                    print(f"   > Aesthetic search: '{aesthetic_query}'...")
                    try:
                        results = run_grid_search(location_string, aesthetic_query, GRID_SIZE)
                        if SUPABASE_ENABLED and results:
                            neighborhood_name = hood.split(',')[0].strip()
                            aesthetic_slug = f"{cuisine_name}_aesthetic"
                            save_batch_to_supabase(results, aesthetic_slug, neighborhood_name)
                    except Exception as e:
                        print(f"   [!] Error in aesthetic search for {cuisine_name} in {hood}: {e}")
                        continue

                    sleep_seconds = random.uniform(5, 12)
                    print(f"   [Waiting {sleep_seconds:.1f}s...]")
                    time.sleep(sleep_seconds)
            
            # Longer pause (20-30s) when switching neighborhoods to let connections reset
            long_sleep = random.uniform(20, 30)
            print(f"   [Changing neighborhoods... Taking a {long_sleep:.0f}s break]")
            time.sleep(long_sleep)

    print("\n--- ALL BATCHES COMPLETE ---")
