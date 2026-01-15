
import os
import sys
import json
import time

# Mocking Supabase and Django path
sys.path.insert(0, os.path.join(os.getcwd(), 'my_new_project'))

def test_dynamic_vibe_fetch():
    from supabase_config import get_supabase_client
    supabase = get_supabase_client()
    
    if not supabase:
        print("❌ Supabase client not available")
        return

    print("Fetching distinct vibes from database...")
    result = supabase.table("venue_vibes").select("vibe_slug").execute()
    if result.data:
        all_vibe_slugs = sorted(list(set([v.get('vibe_slug') for v in result.data if v.get('vibe_slug')])))
        print(f"✅ Found {len(all_vibe_slugs)} unique vibe slugs")
        
        # Test cuisine grouping logic similar to views.py
        cuisine_keywords = {
            'indian': ['indian'],
            'korean': ['korean'],
            'japanese': ['japanese', 'sushi', 'ramen', 'izakaya'],
            'italian': ['italian', 'pizza', 'pasta'],
            'chinese': ['chinese', 'dim_sum', 'dumpling'],
            'thai': ['thai'],
            'vietnamese': ['vietnamese', 'pho'],
            'french': ['french'],
            'mexican': ['mexican', 'taco', 'burrito'],
            'mediterranean': ['greek', 'mediterranean', 'middle_eastern', 'shawarma', 'falafel'],
        }
        
        cuisine_groups = {}
        for cuisine_type, keywords in cuisine_keywords.items():
            cuisine_groups[cuisine_type] = [
                slug for slug in all_vibe_slugs 
                if any(kw in slug.lower() for kw in keywords)
            ]
            print(f"  - {cuisine_type}: {len(cuisine_groups[cuisine_type])} slugs ({cuisine_groups[cuisine_type][:3]}...)")

        # Check for slugs NOT in any cuisine group
        all_grouped_slugs = set()
        for group in cuisine_groups.values():
            all_grouped_slugs.update(group)
        
        non_cuisine_slugs = [s for s in all_vibe_slugs if s not in all_grouped_slugs]
        print(f"\nNon-cuisine vibes ({len(non_cuisine_slugs)}): {non_cuisine_slugs[:10]}...")

if __name__ == "__main__":
    test_dynamic_vibe_fetch()
