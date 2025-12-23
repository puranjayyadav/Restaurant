"""
Google Maps Scraper
A standalone scraper for extracting place data from Google Maps without API keys.
Based on reverse-engineered Google Maps search endpoints.
"""

import json
import time
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple

# Check if requests is installed
try:
    import requests
except ImportError:
    print("Error: 'requests' library is missing. Please run: pip install requests")
    exit(1)


def prepare_data(input_data: str) -> List[Any]:
    """
    Prepares the raw response data for parsing.
    Based on Dart implementation with multiple fallback strategies.
    Handles formats: {"c":0,"d":"...} and [["query", [[...]]]]
    """
    try:
        cleaned = input_data
        
        # Remove /*""*/ at the end if present (6 characters)
        if len(cleaned) >= 6 and cleaned.endswith('/*""*/'):
            cleaned = cleaned[:len(cleaned) - 6]
        
        # First parse the outer JSON object
        try:
            decoder = json.JSONDecoder()
            outer_json, _ = decoder.raw_decode(cleaned)
        except (json.JSONDecodeError, ValueError):
            # Try removing )]}' prefix if present
            if ")]}'" in cleaned:
                index = cleaned.index(")]}'")
                cleaned = cleaned[index + 4:]
                cleaned = cleaned.replace('\n', '').strip()
                try:
                    decoder = json.JSONDecoder()
                    outer_json, _ = decoder.raw_decode(cleaned)
                except:
                    return []
            else:
                return []
        
        # Check if it's the {"c":0,"d":"...} format
        if isinstance(outer_json, dict) and 'd' in outer_json:
            d = outer_json['d']
            
            # If "d" is a string, parse it
            if isinstance(d, str):
                d_cleaned = d
                
                # Remove )]}' prefix if present
                if d_cleaned.startswith(")]}'"):
                    d_cleaned = d_cleaned[4:]
                
                # Remove newlines
                d_cleaned = d_cleaned.replace('\n', '').strip()
                
                try:
                    decoder = json.JSONDecoder()
                    d_parsed, _ = decoder.raw_decode(d_cleaned)
                    
                    # Now extract places from the parsed data
                    if isinstance(d_parsed, list) and len(d_parsed) > 0:
                        first = d_parsed[0]
                        if isinstance(first, list) and len(first) > 1:
                            second = first[1]
                            if isinstance(second, list):
                                results = []
                                for array in second:
                                    if isinstance(array, list) and len(array) > 14:
                                        results.append(array[14])
                                return results
                except (json.JSONDecodeError, ValueError, IndexError, TypeError):
                    pass
            
            # If "d" is already a List, use it directly
            elif isinstance(d, list) and len(d) > 0:
                first = d[0]
                if isinstance(first, list) and len(first) > 1:
                    second = first[1]
                    if isinstance(second, list):
                        results = []
                        for array in second:
                            if isinstance(array, list) and len(array) > 14:
                                results.append(array[14])
                        return results
        
        # Fallback: Try direct array format [["query", [[...]]]]
        test_cleaned = cleaned
        if ")]}'" in test_cleaned:
            index = test_cleaned.index(")]}'")
            test_cleaned = test_cleaned[index + 4:]
        test_cleaned = test_cleaned.replace('\n', '').strip()
        
        if len(test_cleaned) >= 6 and test_cleaned.endswith('/*""*/'):
            test_cleaned = test_cleaned[:len(test_cleaned) - 6]
        
        try:
            decoder = json.JSONDecoder()
            json_data, _ = decoder.raw_decode(test_cleaned)
            if isinstance(json_data, list) and len(json_data) > 0:
                first = json_data[0]
                if isinstance(first, list) and len(first) > 1:
                    second = first[1]
                    if isinstance(second, list):
                        results = []
                        for array in second:
                            if isinstance(array, list) and len(array) > 14:
                                results.append(array[14])
                        return results
        except (json.JSONDecodeError, ValueError, IndexError, TypeError):
            pass
        
        return []
    except Exception:
        return []


def prepare_lookup(data: List[Any]):
    """
    Creates a lookup function that safely accesses nested array indices.
    """
    def lookup(*indexes):
        try:
            result = data
            for idx in indexes:
                result = result[idx]
            return result
        except (IndexError, TypeError, KeyError):
            return None
    return lookup


def find_coordinates(data, depth=0, max_depth=10):
    """Recursively searches for coordinates in the data structure."""
    if depth > max_depth:
        return None
    
    if isinstance(data, list):
        # Look for [lat, long] pattern
        if len(data) == 2 and isinstance(data[0], (int, float)) and isinstance(data[1], (int, float)):
            # Check if values look like lat/long
            if -90 <= data[0] <= 90 and -180 <= data[1] <= 180:
                if abs(data[0]) > 1 or abs(data[1]) > 1: # Avoid [0,0] or very close to it
                    return {'lat': data[0], 'long': data[1]}
        
        # Look for [null, null, lat, long] pattern
        if len(data) >= 4 and data[0] is None and data[1] is None and \
           isinstance(data[2], (int, float)) and isinstance(data[3], (int, float)):
            if -90 <= data[2] <= 90 and -180 <= data[3] <= 180:
                if abs(data[2]) > 1 or abs(data[3]) > 1:
                    return {'lat': data[2], 'long': data[3]}

        for item in data:
            res = find_coordinates(item, depth + 1, max_depth)
            if res:
                return res
    
    elif isinstance(data, dict):
        for value in data.values():
            res = find_coordinates(value, depth + 1, max_depth)
            if res:
                return res
                
    return None

def get_lat_long(lookup, raw_data=None) -> Dict[str, Optional[float]]:
    """Extracts latitude and longitude from place data."""
    lat = lookup(208, 0, 2)
    if not lat:
        lat = lookup(37, 0, 0, 8, 0, 2)
    
    long = lookup(208, 0, 3)
    if not long:
        long = lookup(37, 0, 0, 8, 0, 1)
    
    if not lat or not long:
        # Try recursive search if specific indices fail
        res = find_coordinates(raw_data)
        if res:
            return res
            
    return {'lat': lat, 'long': long}


def get_hours(lookup) -> List[Dict[str, Any]]:
    """Extracts business hours from place data."""
    hours_array = lookup(203, 0)
    if not hours_array:
        return []
    
    hours = []
    for day_data in hours_array:
        if not day_data:
            continue
        day = day_data[0] if len(day_data) > 0 else None
        hours_str = None
        open_24 = None
        close_24 = None
        
        try:
            if len(day_data) > 3 and day_data[3]:
                hours_data = day_data[3]
                if len(hours_data) > 0 and hours_data[0]:
                    hours_str = hours_data[0][0] if len(hours_data[0]) > 0 else None
                    if len(hours_data[0]) > 1 and hours_data[0][1]:
                        open_24 = hours_data[0][1][0][0] if len(hours_data[0][1]) > 0 and len(hours_data[0][1][0]) > 0 else None
                        close_24 = hours_data[0][1][1][0] if len(hours_data[0][1]) > 1 and len(hours_data[0][1][1]) > 0 else None
        except (IndexError, TypeError):
            pass
        
        hours.append({
            'day': day,
            'hours': hours_str,
            'open24Hour': open_24,
            'close24Hour': close_24
        })
    
    return hours


def find_photo_urls(data: Any, depth: int = 0, max_depth: int = 5, max_photos: int = 10) -> List[str]:
    """
    Recursively searches for photo URLs in the data structure.
    """
    photos = []
    if depth > max_depth:
        return photos
    
    if isinstance(data, str):
        # Check if it's a photo URL
        if (('googleusercontent' in data or
             'lh3.googleusercontent' in data or
             'maps.googleapis.com' in data or
             'maps/photo' in data or
             'streetview' in data or
             (data.startswith('http') and
              ('.jpg' in data or '.jpeg' in data or '.png' in data or
               'photo' in data or 'image' in data))) and
            'logo' not in data and
            'icon' not in data and
            'default_user.png' not in data and
            'avatar' not in data):
            photos.append(data.strip())
    
    elif isinstance(data, list):
        for item in data:
            if len(photos) >= max_photos:
                break
            photos.extend(find_photo_urls(item, depth + 1, max_depth, max_photos))
    
    elif isinstance(data, dict):
        for value in data.values():
            if len(photos) >= max_photos:
                break
            photos.extend(find_photo_urls(value, depth + 1, max_depth, max_photos))
    
    return photos


def build_results(prepared_data: List[Any]) -> List[Dict[str, Any]]:
    """Builds structured results from prepared place data."""
    results = []
    
    for place in prepared_data:
        if not place or not isinstance(place, list):
            continue
        
        lookup = prepare_lookup(place)
        
        # Extract basic info
        website = lookup(7, 0)
        if website:
            website = website.replace('/url', '').split('?')[0]
        else:
            website = ''
        
        name = lookup(11)
        if not name:
            continue  # Skip places without names
        
        hours = get_hours(lookup)
        coords = get_lat_long(lookup, place)
        
        # Extract photos
        photos = []
        max_photos = 10
        known_photo_indices = [6, 7, 8, 9, 10, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35]
        
        for idx in known_photo_indices:
            try:
                data = lookup(idx)
                if data:
                    found_photos = find_photo_urls(data, 0, 5, max_photos)
                    photos.extend(found_photos)
                    if len(photos) >= max_photos:
                        break
            except Exception:
                pass
        
        # Comprehensive search if no photos found
        if not photos:
            for idx in range(min(len(place), 200)):
                try:
                    data = lookup(idx)
                    if data:
                        found_photos = find_photo_urls(data, 0, 5, max_photos)
                        photos.extend(found_photos)
                        if len(photos) >= max_photos:
                            break
                except Exception:
                    pass
        
        # Filter and deduplicate photos
        filtered_photos = [
            url for url in photos
            if 'default_user.png' not in url and
            'logo' not in url and
            'icon' not in url and
            'avatar' not in url
        ]
        unique_photos = list(dict.fromkeys(filtered_photos))[:8]  # Preserve order, limit to 8
        photo_objects = [{'url': url, 'photo_url': url} for url in unique_photos]
        
        # Build address components
        street_address = lookup(183, 1, 2) or ''
        city = lookup(183, 1, 3) or ''
        zip_code = lookup(183, 1, 4) or ''
        state = lookup(183, 1, 5) or ''
        country_code = lookup(183, 1, 6) or ''
        full_address = f"{street_address} {city} {state} {zip_code} country_code".strip()
        
        # Build result
        result = {
            'street_address': street_address,
            'city': city,
            'zip': zip_code,
            'state': state,
            'country_code': country_code,
            'full_address': full_address,
            'website': website,
            'avg_rating': lookup(4, 7),
            'total_reviews': lookup(4, 8),
            'name': name,
            'tags': lookup(13) or [],
            'notes': lookup(25, 15, 0, 2),
            'place_id': lookup(78),
            'phone': lookup(178, 0, 0),
            'lat': coords['lat'],
            'long': coords['long'],
            'hours': hours,
            'photos': photo_objects
        }
        
        results.append(result)
    
    return results


def search_place_by_name(place_name: str, retries: int = 0, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Searches for a place by name and returns its coordinates and basic info.
    """
    try:
        # Use a generic location (center of US) to search for the place
        encoded_query = urllib.parse.quote(place_name)
        url = (
            f"https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&"
            f"pb=!4m12!1m3!1d13499.795714815926!2d-95.712891!3d37.09024!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!"
            f"7i20!8i0!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!"
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
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
            'Referrer-Policy': 'origin',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            html = response.text
            
            # Remove /*""*/ at the end
            if len(html) >= 6 and html.endswith('/*""*/'):
                data = html[:len(html) - 6]
            else:
                data = html
            
            prepared_data = prepare_data(data)
            
            if prepared_data:
                place = prepared_data[0]
                lookup = prepare_lookup(place)
                coords = get_lat_long(lookup, place)
                
                if coords['lat'] and coords['long']:
                    return {
                        'name': lookup(11),
                        'lat': coords['lat'],
                        'lon': coords['long'],
                        'place_id': lookup(78),
                        'address': f"{lookup(183, 1, 2) or ''} {lookup(183, 1, 3) or ''}".strip(),
                        'rating': lookup(4, 7),
                        'reviews': lookup(4, 8),
                    }
        
        if retries < max_retries:
            time.sleep(2)
            return search_place_by_name(place_name, retries + 1, max_retries)
        return None
    
    except Exception as e:
        print(f"ERROR: Exception searching for place '{place_name}': {e}")
        if retries < max_retries:
            time.sleep(2)
            return search_place_by_name(place_name, retries + 1, max_retries)
        return None


def get_google_maps_data(
    query: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    place_name: Optional[str] = None,
    zoom: float = 13499.795714815926,
    count: int = 200,
    start: int = 0,
    retries: int = 0,
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    """Fetches places from Google Maps using scraping method."""
    try:
        # If place_name is provided but no coordinates, search for the place first
        if place_name and (lat is None or lon is None):
            print(f"Resolving location: {place_name}...")
            place_info = search_place_by_name(place_name)
            if not place_info:
                print(f"Could not find place: {place_name}")
                return []
            lat = place_info['lat']
            lon = place_info['lon']
            print(f"Targeting: {place_info['name']} ({lat:.4f}, {lon:.4f})")
            
            if not query:
                query = "restaurant"
        
        if lat is None or lon is None:
            raise ValueError("Either lat/lon or place_name must be provided")
        
        encoded_query = urllib.parse.quote(query) if query else urllib.parse.quote("")
        url = (
            f"https://www.google.com/search?tbm=map&authuser=0&hl=en&gl=us&"
            f"pb=!4m12!1m3!1d{zoom}!2d{lon}!3d{lat}!2m3!1f0!2f0!3f0!3m2!1i1920!2i376!4f13.1!"
            f"7i{count}!8i{start}!10b1!12m16!1m1!18b1!2m3!5m1!6e2!20e3!10b1!12b1!13b1!16b1!"
            f"17m1!3e1!20m3!5e2!6b1!14b1!19m4!2m3!1i360!2i120!4i8!20m57!2m2!1i203!2i100!3m2!2i4!5b1!"
            f"6m6!1m2!1i86!2i86!1m2!1i408!2i240!7m42!1m3!1e1!2b0!3e3!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!"
            f"1m3!1e8!2b0!3e3!1m3!1e10!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e9!2b1!3e2!1m3!1e10!2b0!3e3!"
            f"1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e4!2b1!4b1!9b0!22m2!1sSTleZpLoHLy4wN4Ps-iR2Aw!7e81!"
            f"24m98!1m31!13m9!2b1!3b1!4b1!6i1!8b1!9b1!14b1!20b1!25b1!18m20!3b1!4b1!5b1!6b1!9b1!12b1!"
            f"13b1!14b1!17b1!20m2!1e3!1e6!24b1!25b1!26b1!29b1!30m1!2b1!36b1!39m3!2m2!2i1!3i1!43b1!52b1!"
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
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
            'Referrer-Policy': 'origin',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            html = response.text
            
            # Check if response is HTML (error page)
            if html.strip().startswith('<!') or '<html' in html.lower():
                print(f"ERROR: Received HTML response. Status: {response.status_code}")
                if retries < max_retries:
                    time.sleep(2)
                    return get_google_maps_data(query, lat, lon, place_name, zoom, count, start, retries + 1, max_retries)
                return []
            
            if len(html) >= 6 and html.endswith('/*""*/'):
                data = html[:len(html) - 6]
            else:
                data = html
            
            prepared_data = prepare_data(data)
            
            if not prepared_data:
                if retries < max_retries:
                    time.sleep(2)
                    return get_google_maps_data(query, lat, lon, place_name, zoom, count, start, retries + 1, max_retries)
                return []
            
            results = build_results(prepared_data)
            return results
        else:
            print(f"ERROR: HTTP {response.status_code}")
            if retries < max_retries:
                time.sleep(2)
                return get_google_maps_data(query, lat, lon, zoom, count, start, retries + 1, max_retries)
            return []
    
    except Exception as e:
        print(f"ERROR: Exception in Google Maps scraping: {e}")
        if retries < max_retries:
            time.sleep(2)
            return get_google_maps_data(query, lat, lon, zoom, count, start, retries + 1, max_retries)
        return []

if __name__ == "__main__":
    # --- CONFIGURATION: NEW YORK CITY ---
    TARGET_LOCATION = "New York City, NY"
    SEARCH_QUERY = "Italian restaurants"  # Change this to whatever you want to find in NYC
    RESULT_LIMIT = 10
    
    print(f"--- Starting Scraper for {TARGET_LOCATION} ---")
    print(f"Query: '{SEARCH_QUERY}'")
    
    # Run the search
    results = get_google_maps_data(
        query=SEARCH_QUERY,
        place_name=TARGET_LOCATION,
        count=RESULT_LIMIT
    )
    
    if results:
        print(f"\nSuccessfully found {len(results)} places in {TARGET_LOCATION}:")
        print("-" * 60)
        for i, place in enumerate(results, 1):
            name = place.get('name', 'N/A')
            address = place.get('full_address', 'N/A')
            rating = place.get('avg_rating')
            reviews = place.get('total_reviews')
            
            # Simple formatting
            rating_str = f"{rating} stars ({reviews} reviews)" if rating else "No rating"
            
            print(f"{i}. {name}")
            print(f"   Address: {address}")
            print(f"   Rating:  {rating_str}")
            print("-" * 60)
    else:
        print("\nNo results found. Try a different query or check your connection.")
