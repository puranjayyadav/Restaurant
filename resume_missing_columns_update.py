"""
Resume updating missing columns from a specific offset
"""

import os
import sys
from add_missing_columns_to_cockroachdb import (
    get_supabase_client,
    get_cockroachdb_connection,
    update_cockroachdb_records
)

def fetch_from_offset(supabase_client, start_offset: int = 0, batch_size: int = 500):
    """Fetch records starting from a specific offset"""
    if not supabase_client:
        return []
    
    all_records = []
    offset = start_offset
    max_retries = 3
    
    print(f"Fetching data from Supabase starting at offset {offset}...")
    
    try:
        while True:
            retry_count = 0
            batch = None
            
            while retry_count < max_retries:
                try:
                    response = supabase_client.table("lemon8_articles")\
                        .select("url, contained_categories, contained_vibes, title, description, embedding, processing_status")\
                        .range(offset, offset + batch_size - 1)\
                        .execute()
                    
                    batch = response.data
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    if 'timeout' in error_msg.lower() or '57014' in error_msg:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"  Timeout on batch {offset}-{offset+batch_size-1}, retrying ({retry_count}/{max_retries})...")
                            import time
                            time.sleep(2)
                            continue
                        else:
                            print(f"  Failed after {max_retries} retries. Stopping at offset {offset}.")
                            return all_records
                    else:
                        raise
            
            if not batch:
                break
            
            all_records.extend(batch)
            print(f"  Fetched {len(all_records)} records (offset {offset})...")
            
            if len(batch) < batch_size:
                break
            
            offset += batch_size
            import time
            time.sleep(0.5)
        
        print(f"[OK] Total records fetched: {len(all_records)}")
        return all_records
    
    except Exception as e:
        print(f"Error fetching from Supabase: {e}")
        import traceback
        traceback.print_exc()
        return all_records


if __name__ == "__main__":
    start_offset = int(sys.argv[1]) if len(sys.argv) > 1 else 6500
    
    print("=" * 60)
    print(f"Resuming column update from offset {start_offset}")
    print("=" * 60)
    print()
    
    # Connect to Supabase
    supabase_client = get_supabase_client()
    if not supabase_client:
        sys.exit(1)
    
    # Fetch from offset
    records = fetch_from_offset(supabase_client, start_offset)
    if not records:
        print("No more records to fetch.")
        sys.exit(0)
    
    # Connect to CockroachDB
    cockroach_conn = get_cockroachdb_connection()
    if not cockroach_conn:
        sys.exit(1)
    
    # Update data
    updated = update_cockroachdb_records(cockroach_conn, records)
    cockroach_conn.close()
    
    print(f"\n[OK] Updated {updated} records starting from offset {start_offset}")
