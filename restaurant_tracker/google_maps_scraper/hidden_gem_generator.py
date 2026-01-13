"""
Hidden Gem Generator - Google Maps Scraper
Finds unconventional and authentic places based on curated vibes and flavor profiles.
"""

import json
import time
import urllib.parse
import os
import math
import random
import concurrent.futures
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set

# Try to import Supabase storage
try:
    from supabase_storage import save_hidden_gems_batch, supabase
    SUPABASE_ENABLED = supabase is not None
except ImportError:
    SUPABASE_ENABLED = False
    print("Supabase storage module not found. Skipping Supabase integration.")

# Check for API Key
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

# --- 1. DATA STRUCTURES ---

UNCONVENTIONAL_VIBES = {
    "secret_gardens": "privately owned public space atrium conservatory quiet reading garden cloister",
    "urban_ruins": "historical landmark ruins remnant fortress preservation society obscure history",
    "hidden_libraries": "athenaeum private membership library special collections archive rare books reading room",
    "oddities_shops": "curiosities and taxidermy medical antiques natural history oddities metaphysical store",
    "vinyl_listening": "jazz kissa audiophile listening bar high-fidelity sound system vinyl cafe",
    "streetwear_archive": "designer vintage archive streetwear resale sneaker consignment curated thrift",
    "apothecary": "traditional herbalist apothecary botanica bulk herbs holistic natural medicine",
    "pottery_studio": "ceramic studio membership wheel throwing workshop pottery classes open studio",
    "maker_space": "makerspace fabrication lab community woodworking shop laser cutting 3d printing service",
    "analog_gaming": "tabletop gaming cafe TCG store warhammer magic the gathering play space",
    "retro_arcade": "classic pinball parlor retro arcade cabinets amusement center barcade",
    "immersive_art": "immersive experience new media art center interactive installation projection mapping gallery",
    "indie_cinema": "repertory cinema independent movie theater 35mm film screenings arthouse",
    "diy_music": "experimental music venue jazz cellar performance art space warehouse venue"
}

NYC_FLAVOR_QUEST = {
    "roman_trattoria": "cacio e pepe carbonara amatriciana roman trattoria authentic",
    "emilia_romagna": "fresh pasta bolognese modena style authentic",
    "sicilian_roots": "arancini caponata cannoli sicilian street food palermo style",
    "regional_puglia": "orecchiette burrata puglia cuisine bari style",
    "tokyo_alleyway": "izakaya yakitori skewers sake bar omakase counter hidden",
    "kyoto_vibes": "kaiseki tea ceremony matcha house traditional kyoto cuisine",
    "spicy_china": "sichuan peppercorn mapo tofu chongqing hot pot spicy authentic",
    "silk_road_noodles": "biang biang noodles xi'an cuisine hand-pulled noodles cumin lamb",
    "cantonese_comfort": "hong kong cafe congee wonton noodle soup dim sum parlor cart",
    "korean_pocha": "korean pocha street food tent wagon soju tent gopchang",
    "oaxacan_depths": "mole negro oaxaca cuisine mezcaleria tlayuda authentic",
    "peruvian_nikkei": "nikkei cuisine peruvian japanese fusion ceviche tiradito",
    "salvadoran_comfort": "pupuseria loroco revueltas curtido salvadoran authentic",
    "venezuelan_street": "arepa bar cachapas pabellon criollo venezuelan street food",
    "georgian_feasts": "khachapuri adjaruli khinkali georgian wine qvevri tbilisi style",
    "uzbek_silk_road": "lagman noodles plov samsa uzbek cuisine bukharan kosher",
    "ukrainian_village": "varenyky borscht ukrainian diner veselka style pierogi authentic",
    "indian_canteen": "mumbai street food vada pav chaat house indian canteen",
    "south_indian_soul": "dosa thali chennai style idli sambar authentic vegetarian",
    "persian_nights": "tahdig fesenjan kebab koobideh persian rug authentic iran",
    "lebanese_souk": "mezze manakish zaatar labneh arak lebanese authentic",
    "ethiopian_share": "injera platter doro wat berbere ethiopian coffee ceremony hand eating",
    "senegalese_comfort": "thieboudienne jollof rice yassa chicken senegalese harlem authentic"
}

NYC_REGIONS = {
    "Manhattan_South": [
        "Financial District", "Tribeca", "SoHo", "Little Italy", 
        "Chinatown", "Lower East Side", "East Village", 
        "West Village", "Greenwich Village"
    ],
    "Manhattan_Mid": [
        "Chelsea", "Meatpacking District", "Flatiron District", 
        "Gramercy Park", "Midtown West", "Hell's Kitchen", 
        "Koreatown", "Murray Hill", "Midtown East"
    ],
    "Manhattan_North": [
        "Upper West Side", "Upper East Side", "Harlem", 
        "Morningside Heights", "Washington Heights", "Inwood"
    ],
    "Brooklyn_North": [
        "Williamsburg", "Greenpoint", "Bushwick", "East Williamsburg"
    ],
    "Brooklyn_Central_South": [
        "DUMBO", "Brooklyn Heights", "Cobble Hill", "Carroll Gardens",
        "Park Slope", "Bed-Stuy", "Fort Greene", "Clinton Hill", "Red Hook"
    ],
    "Queens": [
        "Long Island City", "Astoria", "Sunnyside", 
        "Jackson Heights", "Flushing", "Ridgewood"
    ],
    "Bronx": [
        "South Bronx", "Arthur Ave", "Belmont", "Mott Haven"
    ]
}

# --- 2. CORE SCRAPER ENGINE (Copied from advanced_grid_scraper.py) ---

def prepare_data(input_data: str) -> List[Any]:
    try:
        cleaned = input_data
        if len(cleaned) >= 6 and cleaned.endswith('/*""*/'):
            cleaned = cleaned[:len(cleaned) - 6]
        
        try:
            decoder = json.JSONDecoder()
            outer_json, _ = decoder.raw_decode(cleaned)
        except (json.JSONDecodeError, ValueError):
            if ")]}'" in cleaned:
                cleaned = cleaned.split(")]}'")[1].strip()
                try:
                    decoder = json.JSONDecoder()
                    outer_json, _ = decoder.raw_decode(cleaned)
                except:
                    return []
            else:
                return []
        
        if isinstance(outer_json, dict) and 'd' in outer_json:
            d = outer_json['d']
            if isinstance(d, str):
                d = d.replace('\n', '').strip()
                if d.startswith(")]}'"):
                    d = d[4:]
                try:
                    d_parsed = json.loads(d)
                    if isinstance(d_parsed, list) and len(d_parsed) > 0:
                        if isinstance(d_parsed[0], list) and len(d_parsed[0]) > 1:
                            if isinstance(d_parsed[0][1], list):
                                return [x[14] for x in d_parsed[0][1] if isinstance(x, list) and len(x) > 14]
                except:
                    pass
            elif isinstance(d, list):
                 if len(d) > 0 and isinstance(d[0], list) and len(d[0]) > 1:
                    if isinstance(d[0][1], list):
                        return [x[14] for x in d[0][1] if isinstance(x, list) and len(x) > 14]

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
        
        photos = []
        known_indices = [6, 7, 8, 9, 10, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35]
        for idx in known_indices:
            p_data = lookup(idx)
            if p_data:
                photos.extend(find_photo_urls(p_data))
                if len(photos) >= 10: break
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

def get_long_lat_grid(place_viewport: Dict[str, Any], grid_size: int = 5) -> List[Tuple[float, float]]:
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

def get_google_maps_data(query: str, lat: float, lon: float, zoom: float = 13500, count: int = 200, start: int = 0) -> List[Dict[str, Any]]:
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
        time.sleep(0.5)
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            return build_results(prepare_data(response.text))
    except Exception as e:
        print(f"Error scraping grid point {lat},{lon}: {e}")
    return []

def run_grid_search(location_name: str, search_query: str, grid_dimension: int = 3) -> List[Dict[str, Any]]:
    print(f"--- Starting Search for '{search_query}' in '{location_name}' ---")
    viewport = None
    place_details = google_maps_api_text_search(location_name)
    if place_details and 'geometry' in place_details:
        viewport = place_details['geometry']['viewport']
    else:
        try:
            from neighborhood_data import get_neighborhood_viewport
            viewport = get_neighborhood_viewport(location_name)
        except:
            pass
    if not viewport:
         viewport = {
            'northeast': {'lat': 40.730, 'lng': -73.990},
            'southwest': {'lat': 40.710, 'lng': -74.010}
        }
    grid = get_long_lat_grid(viewport, grid_dimension)
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for lat, lon in grid:
            futures.append(executor.submit(get_google_maps_data, search_query, lat, lon))
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                data = future.result()
                all_results.extend(data)
                print(f"Finished grid point {i+1}/{len(grid)} - Found {len(data)} places")
            except Exception as e:
                print(f"Grid point failed: {e}")
    unique_places = {}
    for place in all_results:
        pid = place.get('place_id')
        if pid and pid not in unique_places:
            unique_places[pid] = place
    final_results = list(unique_places.values())
    return final_results

# --- 3. RUNNER ---

def main():
    print("\n" + "="*60)
    print("  HIDDEN GEM GENERATOR - FULL CITY SWEEP")
    print("="*60 + "\n")

    # 2. Combine all prompts
    all_vibe_groups = {
        "unconventional": UNCONVENTIONAL_VIBES,
        "flavor_quest": NYC_FLAVOR_QUEST
    }

    # 3. Outer Loop: Regions
    for region_name, neighborhoods in NYC_REGIONS.items():
        print(f"\n🌍 REGION: {region_name}")
        print("-" * 30)
        
        # 4. Middle Loop: Neighborhoods
        # Shuffle neighborhoods to vary the starting point and reduce pattern detection
        random.shuffle(neighborhoods)
        
        for neighborhood in neighborhoods:
            location = f"{neighborhood}, New York, NY"
            print(f"\n📍 Starting Neighborhood: {neighborhood}")
            
            # 5. Inner Loop: Prompt Groups
            for group_name, prompts in all_vibe_groups.items():
                print(f"   📂 Group: {group_name}")
                
                # Shuffle prompts within the group
                prompt_items = list(prompts.items())
                random.shuffle(prompt_items)
                
                for vibe_key, search_query in prompt_items:
                    print(f"      ✨ Searching: {vibe_key}...")
                    
                    try:
                        # Run the search
                        # Using grid_dimension=2 for speed, increase to 3-4 for higher density
                        results = run_grid_search(location, search_query, grid_dimension=2)
                        
                        print(f"      ✨ Found {len(results)} places.")

                        # 5.5 Optional: Sync to Supabase
                        if SUPABASE_ENABLED:
                            save_hidden_gems_batch(
                                results=results,
                                vibe_slug=vibe_key,
                                vibe_group=group_name,
                                neighborhood=neighborhood,
                                region=region_name
                            )
                        
                    except Exception as e:
                        print(f"      ❌ Error searching {vibe_key} in {neighborhood}: {e}")
                    
                    # 6. Safety Delay (Polite Scraping)
                    # We sleep between 3-7 seconds between prompts to avoid rate limiting
                    sleep_time = random.uniform(3, 7)
                    time.sleep(sleep_time)
            
            # Larger gap between neighborhoods
            print(f"\n   --- Finished {neighborhood}. Taking a short break...")
            time.sleep(random.uniform(10, 20))

    print("\n" + "="*60)
    print("  🎉 FULL CITY SWEEP COMPLETE!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
