import os
import psycopg2
from psycopg2.extras import RealDictCursor

def test_filtered_collections():
    conn_string = "postgresql://puranjay:Mo4MAznbTMcufpVAsU6Yzw@tailed-okapi-20468.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full"
    
    try:
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query collections with more than 2 items
        query = """
            SELECT c.*, count(*) as item_count
            FROM collections c
            JOIN collection_items ci ON c.id = ci.collection_id
            GROUP BY c.id, c.name, c.description, c.neighborhood, c.created_at
            HAVING count(*) > 2
            ORDER BY c.created_at DESC
        """
        cur.execute(query)
        results = cur.fetchall()
        
        print(f"Found {len(results)} collections with more than 2 items:")
        for r in results:
            print(f"- {r['name']} ({r['item_count']} items)")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_filtered_collections()
