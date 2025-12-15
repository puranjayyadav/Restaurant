"""
Enrich Lemon8 restaurants with Yelp URLs
Queries Supabase lemon8_articles table, extracts restaurant names from itinerary_data,
and finds their Yelp URLs using the yelp_url_enricher.
"""

import os
import sys
import json
import time
from typing import List, Dict, Optional
from supabase_config import get_supabase_client
from yelp_url_enricher import find_yelp_url

def get_restaurants_from_lemon8_articles(limit: Optional[int] = None) -> List[Dict]:
    """
    Query Supabase lemon8_articles table and extract restaurant names from itinerary_data.
    
    Returns:
        List of dictionaries with restaurant info: {
            'place_name': str,
            'city': str,
            'category': str,
            'notes': str,
            'article_url': str
        }
    """
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Could not connect to Supabase")
        return []
    
    try:
        # Query articles that have itinerary_data
        query = supabase.table("lemon8_articles")\
            .select("url, itinerary_data")\
            .not_.is_("itinerary_data", "null")
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        
        restaurants = []
        seen_places = set()  # Avoid duplicates
        
        for article in response.data:
            article_url = article.get("url")
            itinerary_data = article.get("itinerary_data")
            
            if not itinerary_data:
                continue
            
            # Extract city from itinerary_data
            city = itinerary_data.get("city", "New York")  # Default to NYC
            
            # Extract stops (restaurants/places)
            stops = itinerary_data.get("stops", [])
            
            for stop in stops:
                place_name = stop.get("place_name")
                category = stop.get("category", "Food")
                notes = stop.get("notes", "")
                
                if not place_name:
                    continue
                
                # Create unique key to avoid duplicates
                place_key = f"{place_name.lower()}_{city.lower()}"
                
                if place_key not in seen_places:
                    seen_places.add(place_key)
                    restaurants.append({
                        'place_name': place_name,
                        'city': city,
                        'category': category,
                        'notes': notes,
                        'article_url': article_url
                    })
        
        return restaurants
        
    except Exception as e:
        print(f"ERROR: Failed to query Supabase: {e}")
        import traceback
        traceback.print_exc()
        return []


def enrich_restaurants_with_yelp_urls(restaurants: List[Dict], headless: bool = False, delay: float = 2.0) -> Dict[str, int]:
    """
    Find Yelp URLs for a list of restaurants.
    
    Args:
        restaurants: List of restaurant dictionaries
        headless: Whether to run browser in headless mode
        delay: Delay between requests
    
    Returns:
        Statistics dictionary
    """
    stats = {
        'total': len(restaurants),
        'found': 0,
        'failed': 0,
        'results': []
    }
    
    print(f"\n{'='*60}")
    print(f"Enriching {len(restaurants)} restaurants with Yelp URLs")
    print(f"{'='*60}\n")
    
    for idx, restaurant in enumerate(restaurants, 1):
        place_name = restaurant['place_name']
        city = restaurant['city']
        category = restaurant['category']
        
        print(f"\n[{idx}/{len(restaurants)}] {place_name} ({city}) - {category}")
        print(f"  Article: {restaurant['article_url']}")
        
        try:
            # Try to extract state from city if possible
            state = None
            if city == "New York" or "New York" in city:
                state = "NY"
            elif city == "Brooklyn":
                state = "NY"
                city = "New York"  # Use New York as city for Brooklyn
            
            # Search for Yelp URL
            yelp_url = find_yelp_url(place_name, city, state, headless=headless)
            
            result = {
                'place_name': place_name,
                'city': city,
                'category': category,
                'yelp_url': yelp_url,
                'found': yelp_url is not None
            }
            
            stats['results'].append(result)
            
            if yelp_url:
                stats['found'] += 1
                print(f"  ✓ Found: {yelp_url}")
            else:
                stats['failed'] += 1
                print(f"  ✗ Not found")
            
            # Delay between requests
            if idx < len(restaurants):
                time.sleep(delay)
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            stats['failed'] += 1
            stats['results'].append({
                'place_name': place_name,
                'city': city,
                'category': category,
                'yelp_url': None,
                'found': False,
                'error': str(e)
            })
            time.sleep(delay)
    
    print(f"\n{'='*60}")
    print(f"Enrichment Complete!")
    print(f"Total: {stats['total']}")
    print(f"Found: {stats['found']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success Rate: {(stats['found']/stats['total']*100) if stats['total'] > 0 else 0:.1f}%")
    print(f"{'='*60}\n")
    
    return stats


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Enrich Lemon8 restaurants with Yelp URLs from Supabase'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of articles to process (default: all)'
    )
    parser.add_argument(
        '--visible',
        action='store_true',
        help='Run browser in visible mode (not headless)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--save',
        type=str,
        default=None,
        help='Save results to JSON file (e.g., results.json)'
    )
    
    args = parser.parse_args()
    
    # Get restaurants from database
    print("Querying Supabase for restaurants from Lemon8 articles...")
    restaurants = get_restaurants_from_lemon8_articles(limit=args.limit)
    
    if not restaurants:
        print("No restaurants found in database")
        return
    
    print(f"Found {len(restaurants)} unique restaurants\n")
    
    # Enrich with Yelp URLs
    stats = enrich_restaurants_with_yelp_urls(
        restaurants,
        headless=not args.visible,
        delay=args.delay
    )
    
    # Save results if requested
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.save}")


if __name__ == '__main__':
    main()

