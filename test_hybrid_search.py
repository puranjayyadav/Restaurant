#!/usr/bin/env python3
"""
Test script for hybrid search endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/api"  # Adjust if your server runs on different port

def test_hybrid_search(query, location=None, radius_km=3.0, limit=10):
    """Test the hybrid search endpoint"""
    url = f"{BASE_URL}/hybrid-search/"
    
    payload = {
        "query": query,
        "radius_km": radius_km,
        "limit": limit
    }
    
    if location:
        payload["location"] = location
    
    print(f"\n{'='*60}")
    print(f"Testing Query: '{query}'")
    print(f"{'='*60}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\n[SUCCESS]")
        print(f"Parsed Parameters:")
        print(f"  - Selected Vibe: {data.get('parsed_params', {}).get('selected_vibe', 'None')}")
        print(f"  - Cuisine Preferences: {data.get('parsed_params', {}).get('cuisine_preferences', [])}")
        print(f"  - Social Context: {data.get('parsed_params', {}).get('social_context', 'None')}")
        print(f"\nResults: {data.get('results_count', 0)} venues found")
        print(f"\nTop 5 Results:")
        
        for i, venue in enumerate(data.get('results', [])[:5], 1):
            print(f"\n  {i}. {venue.get('name', 'Unknown')}")
            print(f"     Address: {venue.get('address', 'N/A')}")
            print(f"     Rating: {venue.get('rating', 'N/A')}")
            print(f"     Scores:")
            print(f"       - Semantic: {venue.get('semantic_score', 0):.3f}")
            print(f"       - Vibe Match: {venue.get('vibe_match_score', 0):.3f}")
            print(f"       - Insights: {venue.get('insight_score', 0):.3f}")
            print(f"       - Final: {venue.get('final_score', 0):.3f}")
            if venue.get('matched_vibes'):
                print(f"     Matched Vibes: {', '.join(venue.get('matched_vibes', [])[:3])}")
            if venue.get('display_hook'):
                    hook = venue.get('display_hook', '')
                    if hook:
                        try:
                            print(f"     Hook: {hook}")
                        except UnicodeEncodeError:
                            print(f"     Hook: {hook.encode('ascii', 'replace').decode('ascii')}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR]: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

if __name__ == "__main__":
    # Test queries
    test_queries = [
        {
            "query": "romantic Indian dinner",
            "location": {"lat": 40.7489, "lng": -73.9680},  # Manhattan
        },
        {
            "query": "work friendly coffee in SoHo",
            "location": {"lat": 40.7231, "lng": -74.0026},  # SoHo
        },
        {
            "query": "Korean BBQ",
            "location": {"lat": 40.7489, "lng": -73.9680},  # Koreatown area
        },
        {
            "query": "date night sushi",
            "location": {"lat": 40.7489, "lng": -73.9680},
        },
    ]
    
    print("Testing Hybrid Search System")
    print("="*60)
    
    for test in test_queries:
        test_hybrid_search(**test)
        print("\n" + "-"*60)
    
    print("\nTesting complete!")
