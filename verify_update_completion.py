"""
Verify if all records were successfully updated
Check data consistency and identify any remaining issues
"""

import os
from psycopg2.extras import execute_batch
import psycopg2


def get_cockroachdb_connection():
    """Get CockroachDB connection"""
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


def verify_update_status():
    """Check update status and identify inconsistencies"""
    conn = get_cockroachdb_connection()
    if not conn:
        return
    
    try:
        print("Verify Update Completion")
        print("=" * 60)
        
        # 1. Check if all records have been updated
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.lemon8_articles")
            total = cur.fetchone()[0]
            print(f"Total records: {total}")
            
            # Check exact counts for each column
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(contained_categories) as categories_non_null,
                    COUNT(contained_vibes) as vibes_non_null,
                    COUNT(title) as title_non_null,
                    COUNT(description) as desc_non_null,
                    COUNT(embedding) as embedding_non_null,
                    COUNT(processing_status) as status_non_null
                FROM public.lemon8_articles
            """)
            
            rows = cur.fetchall()
            for row in rows:
                total, cats, vibes, title, desc, embed, status = row
                print(f"\nUpdate Status:")
                print(f"  contained_categories: {cats:,} ({100*row[1]/total:.1f}%)")
                print(f"  contained_vibes: {vibes:,} ({100*row[2]/total:.1f}%)")
                print(f"  title: {title:,} ({100*row[3]/total:.1f}%)")
                print(f"  description: {desc:,} ({100*row[4]/total:.1f}%)")
                print(f"  embedding: {embed:,} ({100*row[5]/total:.1f}%)")
                print(f"  processing_status: {status:,} ({100*row[6]/total:.1f}%)")
            
            # Check for specific weird patterns
            print(f"\nChecking for discrepancies:")
            
            # Records with processing_status but other nulls
            cur.execute("""
                SELECT COUNT(*) FROM public.lemon8_articles
                WHERE processing_status IS NOT NULL 
                AND (contained_categories IS NULL OR contained_vibes IS NULL)
            """)
            weird_processing = cur.fetchone()[0]
            print(f"  Records with processing_status but missing categories/vibes: {weird_processing}")
            
            # Records with only one of contained_categories/vibes
            cur.execute("""
                SELECT COUNT(*) FROM public.lemon8_articles
                WHERE (contained_categories IS NOT NULL AND contained_vibes IS NULL)
                OR (contained_categories IS NULL AND contained_vibes IS NOT NULL)
            """)
            single_contained = cur.fetchone()[0]
            print(f"  Records with only one of contained_categories/vibes: {single_contained}")
            
            # Records with title but no description (or vice versa)
            cur.execute("""
                SELECT COUNT(*) FROM public.lemon8_articles
                WHERE (title IS NOT NULL AND description IS NULL)
                OR (title IS NULL AND description IS NOT NULL)
            """)
            title_desc_mismatch = cur.fetchone()[0]
            print(f"  Records with only title or only description: {title_desc_mismatch}")
            
            # Check for the specific issue we saw - contained_vibes discrepancy
            cur.execute("""
                SELECT COUNT(*) FROM public.lemon8_articles
                WHERE contained_vibes IS NOT NULL
            """)
            vibes_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) FROM public.lemon8_articles
                WHERE contained_categories IS NOT NULL
            """)
            categories_count = cur.fetchone()[0]
            
            if vibes_count != categories_count:
                print(f"  CONTAINED VIBES DISCREPANCY: {vibes_count} vibes vs {categories_count} categories (difference: {abs(vibes_count-categories_count)})")
            
            # Check recent records vs early records 
            print(f"\nChecking recent vs early records:")
            
            cur.execute("""
                SELECT COUNT(*), COUNT(contained_vibes), COUNT(contained_categories)
                FROM (
                    SELECT * FROM public.lemon8_articles 
                    ORDER BY created_at 
                    LIMIT 6500
                ) as early_records
            """)
            early_stats = cur.fetchone()
            
            cur.execute("""
                SELECT COUNT(*), COUNT(contained_vibes), COUNT(contained_categories)
                FROM (
                    SELECT * FROM public.lemon8_articles 
                    ORDER BY created_at DESC
                    LIMIT 6500
                ) as late_records
            """)
            late_stats = cur.fetchone()
            
            print(f"  First 6,500 records (older): vibes={early_stats[1]}, categories={early_stats[2]}")
            print(f"  Last 6,500 records (newer): vibes={late_stats[1]}, categories={late_stats[2]}")
            
            # Show sample records that might have issues
            print(f"\nSample records with only contained_vibes (no categories):")
            cur.execute("""
                SELECT url, contained_vibes, contained_categories, created_at
                FROM public.lemon8_articles
                WHERE contained_vibes IS NOT NULL 
                AND contained_categories IS NULL
                LIMIT 5
            """)
            mismatch_samples = cur.fetchall()
            
            for url, vibes, cats, created in mismatch_samples:
                print(f"  URL: {url[:60]}...")
                print(f"    Vibes: {vibes}")
                print(f"    Categories: {cats}")
                print(f"    Created: {created}")
                print()
    
    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    verify_update_status()