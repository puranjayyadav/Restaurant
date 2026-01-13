#!/usr/bin/env python3
"""Check full_ai_json coverage across the entire dataset"""
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

# Get total count
total_res = supabase.table('place_insights').select('place_id', count='exact').limit(1).execute()
total = total_res.count if hasattr(total_res, 'count') else 0
print(f"Total place_insights entries: {total}")

# Count with full_ai_json (using a more efficient approach)
# Get a larger sample to estimate
print("\nChecking coverage...")

# Method 1: Count entries with full_ai_json
with_data = supabase.table('place_insights').select('place_id').not_.is_('full_ai_json', 'null').execute()
count_with_data = len(with_data.data)

# Since Supabase might paginate, let's check if we got all
# Try to get more if the count is exactly 1000 (common pagination limit)
if count_with_data == 1000:
    print("WARNING: Query returned exactly 1000 results, which might be a pagination limit.")
    print("   Checking if there are more...")
    
    # Try to get entries from different ranges
    offset_1000 = supabase.table('place_insights').select('place_id').not_.is_('full_ai_json', 'null').range(1000, 1999).execute()
    if offset_1000.data:
        count_with_data += len(offset_1000.data)
        print(f"   Found {len(offset_1000.data)} more entries with full_ai_json")

print(f"\nEntries with full_ai_json: {count_with_data}")
print(f"Entries without full_ai_json: {total - count_with_data}")
print(f"Coverage: {(count_with_data / total * 100):.1f}%")

# Check what other useful data exists for entries without full_ai_json
print("\n" + "=" * 50)
print("Checking entries without full_ai_json...")
without_full_ai = supabase.table('place_insights').select('place_id, display_hook, display_short_name, work_friendly').is_('full_ai_json', 'null').limit(10).execute()

if without_full_ai.data:
    print(f"Sample of {len(without_full_ai.data)} entries without full_ai_json:")
    has_display_hook = sum(1 for e in without_full_ai.data if e.get('display_hook'))
    has_display_short_name = sum(1 for e in without_full_ai.data if e.get('display_short_name'))
    print(f"  - Have display_hook: {has_display_hook}/{len(without_full_ai.data)}")
    print(f"  - Have display_short_name: {has_display_short_name}/{len(without_full_ai.data)}")
    
    # Show a sample
    print("\nSample entry:")
    sample = without_full_ai.data[0]
    print(f"  Place ID: {sample.get('place_id')}")
    print(f"  display_hook: {sample.get('display_hook')}")
    print(f"  display_short_name: {sample.get('display_short_name')}")
    print(f"  work_friendly: {sample.get('work_friendly')}")
else:
    print("All sampled entries have full_ai_json")
