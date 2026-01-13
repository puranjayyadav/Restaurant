#!/usr/bin/env python3
"""Check how many venues have rich data (full_ai_json) in place_insights"""
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

# Check total venues (sample query to get count)
total_venues_res = supabase.table('venues').select('place_id', count='exact').limit(1).execute()
print(f"Total venues: {total_venues_res.count if hasattr(total_venues_res, 'count') else 'N/A'}")

# Check total place_insights entries
total_insights_res = supabase.table('place_insights').select('place_id', count='exact').limit(1).execute()
total_insights = total_insights_res.count if hasattr(total_insights_res, 'count') else 'N/A'
print(f"Total place_insights entries: {total_insights}")

# Check venues with full_ai_json (no limit, get all)
insights_with_data = supabase.table('place_insights').select('place_id, full_ai_json').not_.is_('full_ai_json', 'null').execute()
print(f"Venues with full_ai_json: {len(insights_with_data.data)}")

# Check venues without full_ai_json
insights_without_data = supabase.table('place_insights').select('place_id').is_('full_ai_json', 'null').limit(10).execute()
print(f"Sample of venues without full_ai_json: {len(insights_without_data.data)} (showing first 10)")

# Check structure of a sample
if insights_with_data.data:
    sample = insights_with_data.data[0]
    full_ai_json = sample.get('full_ai_json')
    if isinstance(full_ai_json, dict):
        print(f"\nSample full_ai_json keys: {list(full_ai_json.keys())}")
        if 'display_header' in full_ai_json:
            print(f"  - display_header: YES")
        if 'insider_profile' in full_ai_json:
            print(f"  - insider_profile: YES")
        if 'plandit_benchmarks' in full_ai_json:
            print(f"  - plandit_benchmarks: YES")
    else:
        print(f"\nSample full_ai_json type: {type(full_ai_json)}")

# Check for display_hook
insights_with_hook = supabase.table('place_insights').select('place_id, display_hook').not_.is_('display_hook', 'null').execute()
print(f"\nVenues with display_hook: {len(insights_with_hook.data)}")
