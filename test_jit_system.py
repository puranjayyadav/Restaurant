"""
Test script for JIT Real-Time Location System
Tests geohash caching, directional filtering, time-context, and NBA solver
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
project_root = os.path.dirname(os.path.abspath(__file__))
my_new_project_dir = os.path.join(project_root, "my_new_project")
sys.path.insert(0, my_new_project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_new_project.settings")
os.chdir(my_new_project_dir)
django.setup()

from res_backend.geohash_cache import (
    get_geohash, get_cached_places, save_places_to_cache, cleanup_expired_cache
)
from res_backend.utils import (
    calculate_bearing, is_in_forward_cone, filter_directional_places,
    get_time_context_query, get_time_context_label, apply_time_context_filter
)
from res_backend.nba_solver import NBASolver
from django.utils import timezone


def test_geohash():
    """Test geohash calculation"""
    print("\n=== Testing Geohash ===")
    
    # Test coordinates (Soho, NYC)
    lat, lon = 40.7231, -73.9969
    geohash = get_geohash(lat, lon, precision=7)
    print(f"Coordinates: {lat}, {lon}")
    print(f"Geohash (precision 7): {geohash}")
    
    # Test nearby coordinates (should have same or similar geohash)
    lat2, lon2 = 40.7232, -73.9970
    geohash2 = get_geohash(lat2, lon2, precision=7)
    print(f"Nearby coordinates: {lat2}, {lon2}")
    print(f"Geohash 2: {geohash2}")
    print(f"Same cell: {geohash == geohash2}")
    
    return geohash


def test_time_context():
    """Test time-context query mapping"""
    print("\n=== Testing Time Context ===")
    
    test_hours = [8, 11, 13, 15, 18, 22]
    for hour in test_hours:
        context = get_time_context_label(hour)
        queries = get_time_context_query(hour)
        print(f"{hour:02d}:00 -> {context}: {queries}")


def test_directional_filtering():
    """Test directional filtering"""
    print("\n=== Testing Directional Filtering ===")
    
    # User location (Soho)
    user_lat, user_lon = 40.7231, -73.9969
    heading = 0.0  # North
    
    # Test places
    places = [
        {
            'name': 'Place North',
            'lat': 40.7240,  # North of user
            'lng': -73.9969,
            'types': ['restaurant']
        },
        {
            'name': 'Place South',
            'lat': 40.7220,  # South of user
            'lng': -73.9969,
            'types': ['restaurant']
        },
        {
            'name': 'Place East',
            'lat': 40.7231,
            'lng': -73.9950,  # East of user
            'types': ['restaurant']
        },
    ]
    
    # Calculate bearings
    print(f"User location: {user_lat}, {user_lon}, heading: {heading}° (North)")
    for place in places:
        bearing = calculate_bearing(user_lat, user_lon, place['lat'], place['lng'])
        in_cone = is_in_forward_cone(user_lat, user_lon, heading, place['lat'], place['lng'], cone_angle=120)
        print(f"  {place['name']}: bearing={bearing:.1f}°, in_cone={in_cone}")
    
    # Filter places
    filtered = filter_directional_places(places, (user_lat, user_lon), heading, cone_angle=120)
    print(f"\nFiltered places (in forward cone): {len(filtered)}")
    for place in filtered:
        print(f"  - {place['name']} (forward_distance: {place.get('_forward_distance', 0):.0f}m)")


def test_nba_solver():
    """Test NBA solver"""
    print("\n=== Testing NBA Solver ===")
    
    # User location (Soho)
    user_location = (40.7231, -73.9969)
    heading = 0.0  # North
    current_time = timezone.now()
    
    # Sample places
    places = [
        {
            'name': 'Ruby\'s Cafe',
            'lat': 40.7235,
            'lng': -73.9969,
            'rating': 4.5,
            'types': ['restaurant', 'cafe'],
            'place_id': 'test1'
        },
        {
            'name': 'Prince St Pizza',
            'lat': 40.7238,
            'lng': -73.9965,
            'rating': 4.7,
            'types': ['restaurant', 'pizza'],
            'place_id': 'test2'
        },
        {
            'name': 'Far Place',
            'lat': 40.7200,  # South (behind user)
            'lng': -73.9969,
            'rating': 4.8,
            'types': ['restaurant'],
            'place_id': 'test3'
        },
    ]
    
    solver = NBASolver()
    result = solver.solve_next_action(
        user_location=user_location,
        heading=heading,
        current_time=current_time,
        places=places,
        user_preferences=None
    )
    
    print(f"Context: {result['context']}")
    print(f"Confidence: {result['confidence']}")
    if result['next_stop']:
        print(f"\nNext Stop:")
        print(f"  Name: {result['next_stop']['name']}")
        print(f"  Distance: {result['next_stop']['distance_m']}m")
        print(f"  Bearing: {result['next_stop']['bearing']} ({result['next_stop']['bearing_degrees']}°)")
        print(f"  ETA: {result['next_stop']['estimated_arrival']}")
    if result['backup_stop']:
        print(f"\nBackup Stop:")
        print(f"  Name: {result['backup_stop']['name']}")
        print(f"  Distance: {result['backup_stop']['distance_m']}m")
        print(f"  Bearing: {result['backup_stop']['bearing']}")


def test_cache():
    """Test cache operations"""
    print("\n=== Testing Cache ===")
    
    # Test coordinates
    lat, lon = 40.7231, -73.9969
    geohash = get_geohash(lat, lon, precision=7)
    query_context = get_time_context_label(timezone.now().hour)
    
    # Sample places data
    test_places = [
        {
            'name': 'Test Restaurant',
            'lat': 40.7235,
            'lng': -73.9969,
            'rating': 4.5,
            'types': ['restaurant']
        }
    ]
    
    print(f"Geohash: {geohash}, Context: {query_context}")
    
    # Check cache (should be empty initially)
    cached = get_cached_places(geohash, query_context)
    print(f"Cache check (before save): {cached is not None}")
    
    # Save to cache
    save_places_to_cache(geohash, query_context, test_places)
    print("Saved to cache")
    
    # Check cache again (should have data now)
    cached = get_cached_places(geohash, query_context)
    print(f"Cache check (after save): {cached is not None}")
    if cached:
        print(f"  Cached places: {len(cached)}")
        print(f"  First place: {cached[0]['name']}")


def main():
    print("=" * 60)
    print("JIT Real-Time Location System - Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        test_geohash()
        test_time_context()
        test_directional_filtering()
        test_nba_solver()
        test_cache()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        import traceback
        print(f"\nERROR: Test failed: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()

