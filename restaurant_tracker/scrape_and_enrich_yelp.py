"""
Script to scrape Google Maps for nearby places and then enrich them with Yelp URLs.

Usage:
    python scrape_and_enrich_yelp.py --lat 40.7128 --lon -74.0060 --query "restaurant"
    python scrape_and_enrich_yelp.py --place "New York" --query "restaurant"
"""

import os
import sys
import json
import time
import argparse
from typing import List, Dict, Any, Optional

# Import Google Maps scraper
from google_maps_scraper import get_google_maps_data

# Setup Django environment for Yelp enricher
sys.path.append(os.path.join(os.path.dirname(__file__), 'my_new_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
import django
django.setup()

from res_backend.models import ScrapedRestaurant
# Import Yelp enricher functions
import yelp_url_enricher


def save_places_to_json(places: List[Dict[str, Any]], filename: str = "scraped_places.json"):
    """Save scraped places to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(places, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(places)} places to {filename}")


def load_places_from_json(filename: str = "scraped_places.json") -> List[Dict[str, Any]]:
    """Load places from JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        places = json.load(f)
    print(f"✓ Loaded {len(places)} places from {filename}")
    return places


def enrich_places_with_yelp_urls(places: List[Dict[str, Any]], delay: float = 2.0) -> Dict[str, Any]:
    """
    Enrich a list of places with Yelp URLs.
    
    Args:
        places: List of place dictionaries from Google Maps scraper
        delay: Delay between requests (in seconds)
    
    Returns:
        Dictionary with statistics and enriched places
    """
    stats = {
        'total': len(places),
        'found': 0,
        'failed': 0,
        'enriched_places': []
    }
    
    # Use the find_yelp_url function which manages its own driver
    for idx, place in enumerate(places, 1):
        name = place.get('name', '')
        city = place.get('city', '')
        state = place.get('state', '')
        
        if not name:
            print(f"[{idx}/{len(places)}] Skipping - no name")
            stats['failed'] += 1
            continue
        
        print(f"\n[{idx}/{len(places)}] Processing: {name} ({city}, {state})")
        
        # Search for Yelp URL
        try:
            yelp_url = yelp_url_enricher.find_yelp_url(name, city, state, debug=False)
            
            # Add Yelp URL to place data
            place['yelp_url'] = yelp_url
            
            if yelp_url:
                stats['found'] += 1
                print(f"✓ Found Yelp URL: {yelp_url}")
            else:
                stats['failed'] += 1
                print(f"✗ Could not find Yelp URL")
            
            stats['enriched_places'].append(place)
            
            # Delay between requests
            time.sleep(delay)
            
        except Exception as e:
            print(f"ERROR: Failed to process {name}: {e}")
            place['yelp_url'] = None
            place['error'] = str(e)
            stats['failed'] += 1
            stats['enriched_places'].append(place)
            time.sleep(delay)
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Google Maps for places and enrich with Yelp URLs'
    )
    parser.add_argument(
        '--lat',
        type=float,
        default=None,
        help='Latitude for search'
    )
    parser.add_argument(
        '--lon',
        type=float,
        default=None,
        help='Longitude for search'
    )
    parser.add_argument(
        '--place',
        type=str,
        default=None,
        help='Place name to search near (e.g., "New York")'
    )
    parser.add_argument(
        '--query',
        type=str,
        default='restaurant',
        help='Search query (default: restaurant)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=50,
        help='Number of places to scrape (default: 50)'
    )
    parser.add_argument(
        '--json-file',
        type=str,
        default='scraped_places.json',
        help='JSON file to save/load places (default: scraped_places.json)'
    )
    parser.add_argument(
        '--skip-scrape',
        action='store_true',
        help='Skip scraping and use existing JSON file'
    )
    parser.add_argument(
        '--skip-enrich',
        action='store_true',
        help='Skip Yelp enrichment and only scrape'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between Yelp searches (default: 2.0 seconds)'
    )
    
    args = parser.parse_args()
    
    places = []
    
    # Step 1: Scrape Google Maps (unless skipping)
    if not args.skip_scrape:
        print("=" * 60)
        print("Step 1: Scraping Google Maps")
        print("=" * 60)
        
        if args.place:
            print(f"Searching for '{args.query}' near '{args.place}'...")
            places = get_google_maps_data(
                query=args.query,
                place_name=args.place,
                count=args.count
            )
        elif args.lat and args.lon:
            print(f"Searching for '{args.query}' near {args.lat}, {args.lon}...")
            places = get_google_maps_data(
                query=args.query,
                lat=args.lat,
                lon=args.lon,
                count=args.count
            )
        else:
            print("ERROR: Must provide either --lat/--lon or --place")
            return
        
        print(f"\n✓ Found {len(places)} places from Google Maps")
        
        # Save to JSON
        save_places_to_json(places, args.json_file)
    else:
        # Load from existing JSON
        print(f"Loading places from {args.json_file}...")
        places = load_places_from_json(args.json_file)
    
    if not places:
        print("No places to process!")
        return
    
    # Step 2: Enrich with Yelp URLs (unless skipping)
    if not args.skip_enrich:
        print("\n" + "=" * 60)
        print("Step 2: Enriching with Yelp URLs")
        print("=" * 60)
        
        stats = enrich_places_with_yelp_urls(places, delay=args.delay)
        
        # Save enriched results
        enriched_filename = args.json_file.replace('.json', '_enriched.json')
        save_places_to_json(stats['enriched_places'], enriched_filename)
        
        # Print summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Total places: {stats['total']}")
        print(f"Found Yelp URLs: {stats['found']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success rate: {(stats['found']/stats['total']*100) if stats['total'] > 0 else 0:.1f}%")
        print(f"\nEnriched results saved to: {enriched_filename}")
        print("=" * 60)
    else:
        print("\nSkipping Yelp enrichment (--skip-enrich flag set)")


if __name__ == '__main__':
    main()

