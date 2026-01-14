"""
Verify migration from Supabase to CockroachDB

This script:
1. Counts total records in Supabase lemon8_articles
2. Counts total records in CockroachDB lemon8_articles
3. Compares counts
4. Optionally checks sample records for data integrity
5. Identifies any missing URLs
"""

import os
import sys
from typing import List, Set, Dict

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


def count_supabase_records(supabase_client) -> int:
    """Count total records in Supabase"""
    if not supabase_client:
        return -1
    
    try:
        # Use a count query
        response = supabase_client.table("lemon8_articles")\
            .select("url", count="exact")\
            .execute()
        
        # The count is in response.count
        count = response.count if hasattr(response, 'count') else len(response.data)
        return count
    except Exception as e:
        print(f"Error counting Supabase records: {e}")
        # Fallback: try to get all URLs and count
        try:
            all_urls = []
            offset = 0
            batch_size = 1000
            while True:
                response = supabase_client.table("lemon8_articles")\
                    .select("url")\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                if not response.data:
                    break
                
                all_urls.extend([r['url'] for r in response.data])
                if len(response.data) < batch_size:
                    break
                offset += batch_size
            
            return len(all_urls)
        except Exception as e2:
            print(f"Fallback count also failed: {e2}")
            return -1


def count_cockroachdb_records(conn) -> int:
    """Count total records in CockroachDB"""
    if not conn:
        return -1
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.lemon8_articles")
            result = cur.fetchone()
            return result[0] if result else 0
    except Exception as e:
        print(f"Error counting CockroachDB records: {e}")
        return -1


def get_supabase_urls(supabase_client, limit: int = None) -> Set[str]:
    """Get all URLs from Supabase"""
    if not supabase_client:
        return set()
    
    all_urls = set()
    offset = 0
    batch_size = 1000
    
    print("Fetching URLs from Supabase...")
    
    try:
        while True:
            response = supabase_client.table("lemon8_articles")\
                .select("url")\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not response.data:
                break
            
            batch_urls = {r['url'] for r in response.data if r.get('url')}
            all_urls.update(batch_urls)
            
            print(f"  Fetched {len(all_urls)} URLs so far...")
            
            if len(response.data) < batch_size:
                break
            
            if limit and len(all_urls) >= limit:
                break
            
            offset += batch_size
            
            import time
            time.sleep(0.3)  # Small delay
        
        return all_urls
    except Exception as e:
        print(f"Error fetching URLs from Supabase: {e}")
        return all_urls


def get_cockroachdb_urls(conn) -> Set[str]:
    """Get all URLs from CockroachDB"""
    if not conn:
        return set()
    
    all_urls = set()
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT url FROM public.lemon8_articles")
            while True:
                rows = cur.fetchmany(1000)
                if not rows:
                    break
                all_urls.update(row[0] for row in rows if row[0])
                print(f"  Fetched {len(all_urls)} URLs so far...")
        
        return all_urls
    except Exception as e:
        print(f"Error fetching URLs from CockroachDB: {e}")
        return all_urls


def compare_sample_records(supabase_client, conn, sample_size: int = 10):
    """Compare sample records between both databases"""
    if not supabase_client or not conn:
        return
    
    print(f"\nComparing {sample_size} sample records...")
    
    try:
        # Get sample from Supabase
        response = supabase_client.table("lemon8_articles")\
            .select("*")\
            .limit(sample_size)\
            .execute()
        
        supabase_samples = response.data
        
        # Get corresponding records from CockroachDB
        with conn.cursor() as cur:
            matches = 0
            mismatches = 0
            
            for record in supabase_samples:
                url = record.get('url')
                if not url:
                    continue
                
                cur.execute(
                    "SELECT url, itinerary_data, enriched_itinerary_data, scraped_at, extracted_at FROM public.lemon8_articles WHERE url = %s",
                    (url,)
                )
                crdb_record = cur.fetchone()
                
                if crdb_record:
                    matches += 1
                    print(f"  [MATCH] {url[:60]}...")
                else:
                    mismatches += 1
                    print(f"  [MISSING] {url[:60]}...")
            
            print(f"\nSample comparison: {matches} matched, {mismatches} missing")
    
    except Exception as e:
        print(f"Error comparing samples: {e}")


def main():
    """Main verification function"""
    print("=" * 60)
    print("Migration Verification: Supabase -> CockroachDB")
    print("=" * 60)
    print()
    
    # Connect to both databases
    print("Step 1: Connecting to databases...")
    supabase_client = get_supabase_client()
    cockroach_conn = get_cockroachdb_connection()
    
    if not supabase_client:
        print("Failed to connect to Supabase")
        return 1
    
    if not cockroach_conn:
        print("Failed to connect to CockroachDB")
        return 1
    
    print("[OK] Connected to both databases")
    print()
    
    # Count records
    print("Step 2: Counting records...")
    supabase_count = count_supabase_records(supabase_client)
    cockroach_count = count_cockroachdb_records(cockroach_conn)
    
    print(f"Supabase records: {supabase_count}")
    print(f"CockroachDB records: {cockroach_count}")
    print()
    
    # Compare counts
    if supabase_count == -1 or cockroach_count == -1:
        print("[WARNING] Could not get accurate counts. Proceeding with URL comparison...")
    elif supabase_count == cockroach_count:
        print("[SUCCESS] Record counts match!")
    else:
        diff = abs(supabase_count - cockroach_count)
        print(f"[WARNING] Record counts differ by {diff}")
        if supabase_count > cockroach_count:
            print(f"  Missing {diff} records in CockroachDB")
        else:
            print(f"  Extra {diff} records in CockroachDB")
    print()
    
    # Compare URLs (if counts don't match or user wants detailed check)
    if supabase_count != cockroach_count or '--detailed' in sys.argv:
        print("Step 3: Comparing URLs (this may take a while)...")
        supabase_urls = get_supabase_urls(supabase_client)
        cockroach_urls = get_cockroachdb_urls(cockroach_conn)
        
        print()
        print(f"Supabase URLs: {len(supabase_urls)}")
        print(f"CockroachDB URLs: {len(cockroach_urls)}")
        
        missing_urls = supabase_urls - cockroach_urls
        extra_urls = cockroach_urls - supabase_urls
        
        print()
        if not missing_urls and not extra_urls:
            print("[SUCCESS] All URLs match!")
        else:
            if missing_urls:
                print(f"[WARNING] {len(missing_urls)} URLs in Supabase but not in CockroachDB:")
                for url in list(missing_urls)[:10]:  # Show first 10
                    print(f"  - {url}")
                if len(missing_urls) > 10:
                    print(f"  ... and {len(missing_urls) - 10} more")
            
            if extra_urls:
                print(f"[WARNING] {len(extra_urls)} URLs in CockroachDB but not in Supabase:")
                for url in list(extra_urls)[:10]:
                    print(f"  - {url}")
                if len(extra_urls) > 10:
                    print(f"  ... and {len(extra_urls) - 10} more")
        print()
    else:
        print("Step 3: Skipping detailed URL comparison (counts match)")
        print("  Use --detailed flag to force URL comparison")
        print()
    
    # Compare sample records
    print("Step 4: Comparing sample records...")
    compare_sample_records(supabase_client, cockroach_conn, sample_size=10)
    print()
    
    # Close connections
    cockroach_conn.close()
    
    # Final summary
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print(f"Supabase count: {supabase_count}")
    print(f"CockroachDB count: {cockroach_count}")
    
    if supabase_count == cockroach_count and supabase_count > 0:
        print("[SUCCESS] Migration appears complete!")
        return 0
    elif supabase_count > cockroach_count:
        print(f"[INCOMPLETE] Missing {supabase_count - cockroach_count} records")
        return 1
    else:
        print("[WARNING] Counts differ - check details above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
