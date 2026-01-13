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

    # Try to fetch one row to see the columns
    res = supabase.table('lemon8_articles').select('*').limit(1).execute()
    if res.data:
        print("Columns in lemon8_articles:")
        print(json.dumps(res.data[0], indent=2))
    else:
        print("No data found in lemon8_articles")

if __name__ == "__main__":
    check_schema()
