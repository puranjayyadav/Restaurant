"""
Check if Supabase actually has data in the new columns
"""

import os
from supabase import create_client

def get_supabase_client():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY not set")
        return None
    
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None

def check_column_data():
    supabase = get_supabase_client()
    if not supabase:
        return
    
    # Get a sample of records
    response = supabase.table("lemon8_articles")\
        .select("url, contained_categories, contained_vibes, title, description, embedding, processing_status")\
        .limit(10)\
        .execute()
    
    print("Sample records from Supabase:")
    print("=" * 80)
    
    for i, record in enumerate(response.data, 1):
        print(f"\nRecord {i}: {record.get('url', 'N/A')[:60]}...")
        print(f"  contained_categories: {record.get('contained_categories')}")
        print(f"  contained_vibes: {record.get('contained_vibes')}")
        print(f"  title: {record.get('title')}")
        print(f"  description: {record.get('description')[:100] if record.get('description') else None}...")
        print(f"  embedding: {'Present' if record.get('embedding') else 'NULL'} ({len(record.get('embedding', [])) if record.get('embedding') else 0} values)")
        print(f"  processing_status: {record.get('processing_status')}")
    
    # Count non-null
    print("\n" + "=" * 80)
    print("Checking counts...")
    
    # Get total count
    total_response = supabase.table("lemon8_articles")\
        .select("url", count="exact")\
        .execute()
    
    total = total_response.count if hasattr(total_response, 'count') else len(total_response.data)
    print(f"Total records: {total}")
    
    # Check a sample for non-null values
    sample_response = supabase.table("lemon8_articles")\
        .select("url, contained_categories, contained_vibes, title, description, embedding, processing_status")\
        .limit(1000)\
        .execute()
    
    sample = sample_response.data
    categories_count = sum(1 for r in sample if r.get('contained_categories'))
    vibes_count = sum(1 for r in sample if r.get('contained_vibes'))
    title_count = sum(1 for r in sample if r.get('title'))
    desc_count = sum(1 for r in sample if r.get('description'))
    embedding_count = sum(1 for r in sample if r.get('embedding'))
    status_count = sum(1 for r in sample if r.get('processing_status'))
    
    print(f"\nIn sample of {len(sample)} records:")
    print(f"  contained_categories: {categories_count} non-null ({100.0*categories_count/len(sample):.1f}%)")
    print(f"  contained_vibes: {vibes_count} non-null ({100.0*vibes_count/len(sample):.1f}%)")
    print(f"  title: {title_count} non-null ({100.0*title_count/len(sample):.1f}%)")
    print(f"  description: {desc_count} non-null ({100.0*desc_count/len(sample):.1f}%)")
    print(f"  embedding: {embedding_count} non-null ({100.0*embedding_count/len(sample):.1f}%)")
    print(f"  processing_status: {status_count} non-null ({100.0*status_count/len(sample):.1f}%)")

if __name__ == "__main__":
    check_column_data()
