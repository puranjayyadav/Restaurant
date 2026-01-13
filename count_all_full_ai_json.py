#!/usr/bin/env python3
"""Count all entries with full_ai_json using pagination"""
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

# Count using pagination
total_count = 0
page_size = 1000
offset = 0

print("Counting entries with full_ai_json...")

while True:
    result = supabase.table('place_insights').select('place_id', count='exact').not_.is_('full_ai_json', 'null').range(offset, offset + page_size - 1).execute()
    
    if not result.data:
        break
    
    batch_count = len(result.data)
    total_count += batch_count
    
    print(f"  Batch {offset // page_size + 1}: {batch_count} entries (total so far: {total_count})")
    
    if batch_count < page_size:
        break
    
    offset += page_size

# Get total count
total_res = supabase.table('place_insights').select('place_id', count='exact').limit(1).execute()
total = total_res.count if hasattr(total_res, 'count') else 0

print(f"\n{'='*50}")
print(f"Total place_insights entries: {total}")
print(f"Entries with full_ai_json: {total_count}")
print(f"Entries without full_ai_json: {total - total_count}")
print(f"Coverage: {(total_count / total * 100):.1f}%")
