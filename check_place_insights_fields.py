#!/usr/bin/env python3
"""Check what fields are available in place_insights"""
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

# Get a sample of place_insights to see what fields exist
sample = supabase.table('place_insights').select('*').limit(5).execute()

if sample.data:
    print("Sample place_insights entry fields:")
    print("=" * 50)
    for key in sample.data[0].keys():
        print(f"  - {key}")
    
    print("\n" + "=" * 50)
    print("Field coverage (first 100 entries):")
    
    # Check field coverage
    sample_100 = supabase.table('place_insights').select('*').limit(100).execute()
    
    fields_to_check = ['full_ai_json', 'display_hook', 'display_short_name', 'work_friendly', 'is_trap', 'safety_flag']
    
    for field in fields_to_check:
        count = sum(1 for entry in sample_100.data if entry.get(field) is not None)
        print(f"  {field}: {count}/100 ({count}%)")
    
    # Check if entries without full_ai_json have other useful data
    print("\n" + "=" * 50)
    print("Entries without full_ai_json (sample):")
    without_full_ai = supabase.table('place_insights').select('place_id, display_hook, display_short_name, work_friendly, is_trap').is_('full_ai_json', 'null').limit(5).execute()
    
    if without_full_ai.data:
        for entry in without_full_ai.data[:3]:
            print(f"\n  Place ID: {entry.get('place_id')}")
            print(f"    display_hook: {entry.get('display_hook')}")
            print(f"    display_short_name: {entry.get('display_short_name')}")
            print(f"    work_friendly: {entry.get('work_friendly')}")
            print(f"    is_trap: {entry.get('is_trap')}")
    else:
        print("  (All sampled entries have full_ai_json)")
