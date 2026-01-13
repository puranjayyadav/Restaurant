#!/usr/bin/env python3
"""Check if venues have cuisine slugs in venue_vibes"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'my_new_project'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from supabase import create_client
from decouple import config

SUPABASE_URL = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
SUPABASE_KEY = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("❌ Supabase credentials missing!")
    exit(1)

# Check if any venues have indian_north or indian_south as vibe_slug
cuisine_slugs = ['indian_north', 'indian_south']

print("Checking for cuisine slugs in venue_vibes...")
for cuisine in cuisine_slugs:
    result = supabase.table('venue_vibes').select('place_id, vibe_slug').eq('vibe_slug', cuisine).limit(5).execute()
    print(f"\n{cuisine}: {len(result.data)} venues found")
    if result.data:
        print(f"  Sample place_ids: {[r['place_id'] for r in result.data[:3]]}")

# Check what vibe_slugs exist that might be related to Indian cuisine
print("\n" + "="*50)
print("Searching for Indian-related vibe_slugs...")
all_vibes = supabase.table('venue_vibes').select('vibe_slug').limit(1000).execute()
unique_vibes = set([v.get('vibe_slug') for v in all_vibes.data if v.get('vibe_slug')])
indian_related = [v for v in unique_vibes if 'indian' in v.lower()]
print(f"Indian-related vibe_slugs found: {indian_related}")

# Check total count of venues with these cuisine slugs
if indian_related:
    for vibe in indian_related:
        count = supabase.table('venue_vibes').select('place_id', count='exact').eq('vibe_slug', vibe).limit(1).execute()
        print(f"  {vibe}: {count.count if hasattr(count, 'count') else 'N/A'} venues")
