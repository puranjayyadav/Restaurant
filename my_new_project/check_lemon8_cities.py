from supabase import create_client
import os
from decouple import config
import json

def get_supabase_client():
    url = config('SUPABASE_URL', default='')
    key = config('SUPABASE_SERVICE_ROLE_KEY', default=config('SUPABASE_SERVICE_KEY', default=config('SUPABASE_KEY', default='')))
    
    if not url or not key:
        print(f"DEBUG: get_supabase_client failed. URL: {bool(url)}, KEY: {bool(key)}")
        return None
    return create_client(url, key)

def check_schema():
    supabase = get_supabase_client()
    if not supabase:
        print("Supabase client not initialized")
        return

    res = supabase.table('lemon8_articles').select('*').limit(1).execute()
    if res.data:
        print("Keys in lemon8_articles:", res.data[0].keys())
        # Check if 'city' exists and what values it has
        distinct_cities = supabase.table('lemon8_articles').select('city').execute()
        cities = set(d['city'] for d in distinct_cities.data if d.get('city'))
        print("Total cities found:", len(cities))
        print("First 10 distinct cities:", list(cities)[:10])
    else:
        print("No data found in lemon8_articles")

if __name__ == "__main__":
    check_schema()
