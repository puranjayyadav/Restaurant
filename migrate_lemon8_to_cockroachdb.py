"""
Migrate lemon8_articles table from Supabase to CockroachDB

This script:
1. Connects to Supabase and fetches all data from public.lemon8_articles
2. Connects to CockroachDB
3. Creates the table schema in CockroachDB
4. Inserts all data into CockroachDB

Requirements:
- pip install supabase psycopg2-binary python-decouple
- Set environment variables:
  - SUPABASE_URL, SUPABASE_KEY (for source)
  - COCKROACHDB_URL (for destination)
"""

import os
import sys
from typing import List, Dict, Optional
import json
from datetime import datetime

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
    PSYCOPG2_AVAILABLE = True
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    PSYCOPG2_AVAILABLE = False


def get_supabase_client():
    """Get Supabase client for reading data"""
    if not SUPABASE_AVAILABLE:
        return None
    
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY not set in environment variables")
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
    
    # Get connection string from environment
    conn_string = os.getenv("COCKROACHDB_URL", "")
    
    if not conn_string:
        print("Error: COCKROACHDB_URL not set in environment variables")
        print("Format: postgresql://user:password@host:port/database?sslmode=verify-full")
        return None
    
    try:
        # Parse connection string to extract components
        import urllib.parse
        parsed = urllib.parse.urlparse(conn_string)
        
        # Build connection parameters
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 26257,
            'database': parsed.path.lstrip('/') or 'defaultdb',
            'user': parsed.username,
            'password': parsed.password,
        }
        
        # Handle SSL mode
        query_params = urllib.parse.parse_qs(parsed.query)
        sslmode = query_params.get('sslmode', ['require'])[0]
        
        # For verify-full, we need the certificate
        if sslmode == 'verify-full':
            # Try to find the certificate in common locations
            cert_paths = [
                os.path.join(os.getenv('APPDATA', ''), 'postgresql', 'root.crt'),  # Windows
                os.path.expanduser('~/.postgresql/root.crt'),  # Linux/Mac
                os.path.join(os.getenv('HOME', ''), '.postgresql', 'root.crt'),  # Alternative
            ]
            
            cert_path = None
            for path in cert_paths:
                if path and os.path.exists(path):
                    cert_path = path
                    break
            
            if cert_path:
                conn_params['sslmode'] = 'verify-full'
                conn_params['sslrootcert'] = cert_path
                print(f"Using SSL certificate: {cert_path}")
            else:
                print("Warning: Certificate not found. Falling back to require mode.")
                print("Download certificate using:")
                print("  mkdir -p $env:appdata\\postgresql\\")
                print("  Invoke-WebRequest -Uri https://cockroachlabs.cloud/clusters/5ce4244a-90f1-4a00-9b6b-da01d25d67c2/cert -OutFile $env:appdata\\postgresql\\root.crt")
                conn_params['sslmode'] = 'require'
        else:
            conn_params['sslmode'] = sslmode
        
        conn = psycopg2.connect(**conn_params)
        return conn
    except Exception as e:
        print(f"Error connecting to CockroachDB: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_cockroachdb_schema(conn):
    """Create the lemon8_articles table schema in CockroachDB"""
    schema_sql = """
    CREATE TABLE IF NOT EXISTS public.lemon8_articles (
        url TEXT PRIMARY KEY,
        html_content TEXT,
        itinerary_data JSONB,
        enriched_itinerary_data JSONB,
        stops_lat DOUBLE PRECISION[],
        stops_lng DOUBLE PRECISION[],
        scraped_at TIMESTAMP,
        extracted_at TIMESTAMP,
        extraction_error TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_lemon8_articles_extracted_at ON public.lemon8_articles(extracted_at);
    CREATE INDEX IF NOT EXISTS idx_lemon8_articles_created_at ON public.lemon8_articles(created_at);
    CREATE INDEX IF NOT EXISTS idx_lemon8_articles_itinerary_data ON public.lemon8_articles USING GIN (itinerary_data);
    CREATE INDEX IF NOT EXISTS idx_lemon8_articles_enriched_itinerary_data ON public.lemon8_articles USING GIN (enriched_itinerary_data);
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
        print("[OK] Schema created successfully in CockroachDB")
        return True
    except Exception as e:
        print(f"Error creating schema: {e}")
        conn.rollback()
        return False


def fetch_all_from_supabase(supabase_client, batch_size: int = 500) -> List[Dict]:
    """Fetch all records from Supabase lemon8_articles table"""
    if not supabase_client:
        return []
    
    all_records = []
    offset = 0
    max_retries = 3
    
    print("Fetching data from Supabase...")
    
    try:
        while True:
            retry_count = 0
            batch = None
            
            # Retry logic for timeouts
            while retry_count < max_retries:
                try:
                    # Fetch batch with smaller size to avoid timeouts
                    response = supabase_client.table("lemon8_articles")\
                        .select("*")\
                        .range(offset, offset + batch_size - 1)\
                        .execute()
                    
                    batch = response.data
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    error_msg = str(e)
                    if 'timeout' in error_msg.lower() or '57014' in error_msg:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"  Timeout on batch {offset}-{offset+batch_size-1}, retrying ({retry_count}/{max_retries})...")
                            import time
                            time.sleep(2)  # Wait before retry
                            continue
                        else:
                            print(f"  Failed after {max_retries} retries. Stopping fetch.")
                            return all_records
                    else:
                        raise  # Re-raise if it's not a timeout error
            
            if not batch:
                break
            
            all_records.extend(batch)
            print(f"  Fetched {len(all_records)} records so far...")
            
            if len(batch) < batch_size:
                break
            
            offset += batch_size
            
            # Small delay between batches to avoid overwhelming the API
            import time
            time.sleep(0.5)
        
        print(f"[OK] Total records fetched: {len(all_records)}")
        return all_records
    
    except Exception as e:
        print(f"Error fetching from Supabase: {e}")
        import traceback
        traceback.print_exc()
        return all_records


def insert_into_cockroachdb(conn, records: List[Dict], batch_size: int = 100):
    """Insert records into CockroachDB"""
    if not records:
        print("No records to insert")
        return 0
    
    insert_sql = """
    INSERT INTO public.lemon8_articles (
        url, html_content, itinerary_data, enriched_itinerary_data,
        stops_lat, stops_lng, scraped_at, extracted_at,
        extraction_error, created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (url) DO UPDATE SET
        html_content = EXCLUDED.html_content,
        itinerary_data = EXCLUDED.itinerary_data,
        enriched_itinerary_data = EXCLUDED.enriched_itinerary_data,
        stops_lat = EXCLUDED.stops_lat,
        stops_lng = EXCLUDED.stops_lng,
        scraped_at = EXCLUDED.scraped_at,
        extracted_at = EXCLUDED.extracted_at,
        extraction_error = EXCLUDED.extraction_error,
        updated_at = EXCLUDED.updated_at
    """
    
    # Prepare data for insertion
    data_to_insert = []
    for record in records:
        # Convert JSONB fields
        itinerary_data = None
        enriched_itinerary_data = None
        
        if record.get('itinerary_data'):
            if isinstance(record['itinerary_data'], str):
                try:
                    itinerary_data = json.loads(record['itinerary_data'])
                except:
                    itinerary_data = record['itinerary_data']
            else:
                itinerary_data = record['itinerary_data']
        
        if record.get('enriched_itinerary_data'):
            if isinstance(record['enriched_itinerary_data'], str):
                try:
                    enriched_itinerary_data = json.loads(record['enriched_itinerary_data'])
                except:
                    enriched_itinerary_data = record['enriched_itinerary_data']
            else:
                enriched_itinerary_data = record['enriched_itinerary_data']
        
        # Convert arrays
        stops_lat = record.get('stops_lat') or []
        stops_lng = record.get('stops_lng') or []
        
        # Convert timestamps
        scraped_at = record.get('scraped_at')
        extracted_at = record.get('extracted_at')
        created_at = record.get('created_at')
        updated_at = record.get('updated_at')
        
        data_to_insert.append((
            record.get('url'),
            record.get('html_content'),
            json.dumps(itinerary_data) if itinerary_data else None,
            json.dumps(enriched_itinerary_data) if enriched_itinerary_data else None,
            stops_lat if stops_lat else None,
            stops_lng if stops_lng else None,
            scraped_at,
            extracted_at,
            record.get('extraction_error'),
            created_at,
            updated_at
        ))
    
    # Insert in batches
    inserted_count = 0
    try:
        with conn.cursor() as cur:
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i + batch_size]
                execute_batch(cur, insert_sql, batch)
                inserted_count += len(batch)
                print(f"  Inserted {inserted_count}/{len(data_to_insert)} records...")
        
        conn.commit()
        print(f"[OK] Successfully inserted {inserted_count} records into CockroachDB")
        return inserted_count
    
    except Exception as e:
        print(f"Error inserting into CockroachDB: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return inserted_count


def main():
    """Main migration function"""
    print("=" * 60)
    print("Migrating lemon8_articles from Supabase to CockroachDB")
    print("=" * 60)
    print()
    
    # Step 1: Connect to Supabase
    print("Step 1: Connecting to Supabase...")
    supabase_client = get_supabase_client()
    if not supabase_client:
        print("Failed to connect to Supabase. Exiting.")
        return 1
    print("[OK] Connected to Supabase")
    print()
    
    # Step 2: Fetch all data
    print("Step 2: Fetching data from Supabase...")
    records = fetch_all_from_supabase(supabase_client)
    if not records:
        print("No records found in Supabase. Exiting.")
        return 1
    print()
    
    # Step 3: Connect to CockroachDB
    print("Step 3: Connecting to CockroachDB...")
    cockroach_conn = get_cockroachdb_connection()
    if not cockroach_conn:
        print("Failed to connect to CockroachDB. Exiting.")
        return 1
    print("[OK] Connected to CockroachDB")
    print()
    
    # Step 4: Create schema
    print("Step 4: Creating schema in CockroachDB...")
    if not create_cockroachdb_schema(cockroach_conn):
        print("Failed to create schema. Exiting.")
        cockroach_conn.close()
        return 1
    print()
    
    # Step 5: Insert data
    print("Step 5: Inserting data into CockroachDB...")
    inserted = insert_into_cockroachdb(cockroach_conn, records)
    print()
    
    # Step 6: Close connection
    cockroach_conn.close()
    
    # Summary
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Records fetched from Supabase: {len(records)}")
    print(f"Records inserted into CockroachDB: {inserted}")
    print("=" * 60)
    
    return 0 if inserted == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
