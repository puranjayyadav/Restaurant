"""
Add missing columns to CockroachDB lemon8_articles table
and backfill data from Supabase

Missing columns identified:
- contained_categories (ARRAY)
- contained_vibes (ARRAY)
- title (TEXT)
- description (TEXT)
- embedding (ARRAY/FLOAT[])
- processing_status (TEXT)
"""

import os
import sys
import json
from typing import List, Dict

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Supabase imports
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("Error: supabase library not installed. Run: pip install supabase")
    SUPABASE_AVAILABLE = False

# CockroachDB imports
try:
    import psycopg2
    from psycopg2.extras import execute_batch
    from psycopg2 import errors as psycopg2_errors
    PSYCOPG2_AVAILABLE = True
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    PSYCOPG2_AVAILABLE = False


def get_supabase_client():
    """Get Supabase client"""
    if not SUPABASE_AVAILABLE:
        return None
    
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


def get_cockroachdb_connection():
    """Get CockroachDB connection"""
    if not PSYCOPG2_AVAILABLE:
        return None
    
    conn_string = os.getenv("COCKROACHDB_URL", "")
    if not conn_string:
        print("Error: COCKROACHDB_URL not set")
        return None
    
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(conn_string)
        
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 26257,
            'database': parsed.path.lstrip('/') or 'defaultdb',
            'user': parsed.username,
            'password': parsed.password,
        }
        
        query_params = urllib.parse.parse_qs(parsed.query)
        sslmode = query_params.get('sslmode', ['require'])[0]
        
        if sslmode == 'verify-full':
            cert_paths = [
                os.path.join(os.getenv('APPDATA', ''), 'postgresql', 'root.crt'),
                os.path.expanduser('~/.postgresql/root.crt'),
            ]
            
            cert_path = None
            for path in cert_paths:
                if path and os.path.exists(path):
                    cert_path = path
                    break
            
            if cert_path:
                conn_params['sslmode'] = 'verify-full'
                conn_params['sslrootcert'] = cert_path
        
        return psycopg2.connect(**conn_params)
    except Exception as e:
        print(f"Error connecting to CockroachDB: {e}")
        return None


def add_missing_columns(conn):
    """Add missing columns to CockroachDB table"""
    alter_sql = """
    -- Add missing columns if they don't exist
    ALTER TABLE public.lemon8_articles 
    ADD COLUMN IF NOT EXISTS contained_categories TEXT[],
    ADD COLUMN IF NOT EXISTS contained_vibes TEXT[],
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS embedding FLOAT[],
    ADD COLUMN IF NOT EXISTS processing_status TEXT;
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(alter_sql)
        conn.commit()
        print("[OK] Missing columns added successfully")
        return True
    except Exception as e:
        print(f"Error adding columns: {e}")
        conn.rollback()
        return False


def fetch_missing_data_from_supabase(supabase_client, batch_size: int = 500) -> List[Dict]:
    """Fetch records with missing columns from Supabase"""
    if not supabase_client:
        return []
    
    all_records = []
    offset = 0
    max_retries = 3
    
    print("Fetching data with missing columns from Supabase...")
    
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
            print(f"  Fetched {len(all_records)} records so far...")
            
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


def update_cockroachdb_records(conn, records: List[Dict], batch_size: int = 50):
    """Update CockroachDB records with missing column data
    Uses smaller batches and retry logic for CockroachDB transaction retries
    """
    if not records:
        print("No records to update")
        return 0
    
    update_sql = """
    UPDATE public.lemon8_articles SET
        contained_categories = %s,
        contained_vibes = %s,
        title = %s,
        description = %s,
        embedding = %s,
        processing_status = %s
    WHERE url = %s
    """
    
    # Prepare data for update
    data_to_update = []
    for record in records:
        url = record.get('url')
        if not url:
            continue
        
        # Handle arrays
        contained_categories = record.get('contained_categories') or []
        contained_vibes = record.get('contained_vibes') or []
        
        # Handle embedding - convert to list if it's a string
        embedding = record.get('embedding')
        if embedding:
            if isinstance(embedding, str):
                try:
                    embedding = json.loads(embedding)
                except:
                    embedding = None
            elif not isinstance(embedding, list):
                embedding = None
        
        data_to_update.append((
            contained_categories if contained_categories else None,
            contained_vibes if contained_vibes else None,
            record.get('title'),
            record.get('description'),
            embedding if embedding else None,
            record.get('processing_status'),
            url
        ))
    
    # Update in smaller batches with retry logic for CockroachDB
    updated_count = 0
    max_retries = 5
    import time
    
    try:
        for i in range(0, len(data_to_update), batch_size):
            batch = data_to_update[i:i + batch_size]
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    with conn.cursor() as cur:
                        execute_batch(cur, update_sql, batch)
                    conn.commit()
                    updated_count += len(batch)
                    print(f"  Updated {updated_count}/{len(data_to_update)} records...")
                    success = True
                    
                except psycopg2_errors.SerializationFailure as e:
                    # CockroachDB transaction retry error
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = (2 ** retry_count) * 0.1  # Exponential backoff
                        print(f"  Transaction retry {retry_count}/{max_retries}, waiting {wait_time:.2f}s...")
                        time.sleep(wait_time)
                        conn.rollback()
                    else:
                        print(f"  Failed after {max_retries} retries for batch {i}-{i+len(batch)-1}")
                        conn.rollback()
                        # Continue with next batch
                        break
                        
                except Exception as e:
                    print(f"Error updating batch {i}-{i+len(batch)-1}: {e}")
                    conn.rollback()
                    break
        
        print(f"[OK] Successfully updated {updated_count} records in CockroachDB")
        return updated_count
    
    except Exception as e:
        print(f"Error updating CockroachDB: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return updated_count


def main():
    """Main function"""
    print("=" * 60)
    print("Adding Missing Columns to CockroachDB")
    print("=" * 60)
    print()
    
    # Step 1: Connect to CockroachDB
    print("Step 1: Connecting to CockroachDB...")
    cockroach_conn = get_cockroachdb_connection()
    if not cockroach_conn:
        print("Failed to connect to CockroachDB. Exiting.")
        return 1
    print("[OK] Connected to CockroachDB")
    print()
    
    # Step 2: Add missing columns
    print("Step 2: Adding missing columns...")
    if not add_missing_columns(cockroach_conn):
        print("Failed to add columns. Exiting.")
        cockroach_conn.close()
        return 1
    print()
    
    # Step 3: Connect to Supabase
    print("Step 3: Connecting to Supabase...")
    supabase_client = get_supabase_client()
    if not supabase_client:
        print("Failed to connect to Supabase. Exiting.")
        cockroach_conn.close()
        return 1
    print("[OK] Connected to Supabase")
    print()
    
    # Step 4: Fetch missing data
    print("Step 4: Fetching missing column data from Supabase...")
    records = fetch_missing_data_from_supabase(supabase_client)
    if not records:
        print("No records found. Exiting.")
        cockroach_conn.close()
        return 1
    print()
    
    # Step 5: Update CockroachDB
    print("Step 5: Updating CockroachDB records...")
    updated = update_cockroachdb_records(cockroach_conn, records)
    print()
    
    # Step 6: Close connection
    cockroach_conn.close()
    
    # Summary
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Records fetched from Supabase: {len(records)}")
    print(f"Records updated in CockroachDB: {updated}")
    print("=" * 60)
    
    return 0 if updated == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
