import os
import psycopg2
from psycopg2.extras import RealDictCursor

def explore_collection():
    conn_string = os.getenv("COCKROACHDB_URL")
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    collection_id = '0025c06b-d263-4398-a07a-582753cd89ed'
    
    # 1. Get items in collection
    cur.execute("SELECT * FROM collection_items WHERE collection_id = %s", (collection_id,))
    items = cur.fetchall()
    print(f"--- Items in Collection {collection_id} ---")
    for item in items:
        print(item)
    
    # 2. Check restaurant_analysis columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'restaurant_analysis'")
    cols = [c['column_name'] for c in cur.fetchall()]
    print(f"\n--- Columns in restaurant_analysis ---\n{cols}")
    
    # 3. Try to join and get names if columns permit
    if 'id' in cols and ('name' in cols or 'restaurant_name' in cols):
        name_col = 'name' if 'name' in cols else 'restaurant_name'
        query = f"""
            SELECT ra.{name_col}, ci.* 
            FROM collection_items ci
            JOIN restaurant_analysis ra ON ci.restaurant_id::text = ra.id::text
            WHERE ci.collection_id = %s
        """
        try:
            cur.execute(query, (collection_id,))
            joined = cur.fetchall()
            print(f"\n--- Joined Restaurant Info ---")
            for r in joined:
                print(r)
        except Exception as e:
            print(f"\nJoin failed: {e}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    explore_collection()
