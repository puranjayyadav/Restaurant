import os
import psycopg2
from psycopg2.extras import RealDictCursor

def explore_collection():
    # Hardcoding URL for absolute certainty in this terminal session
    conn_string = "postgresql://puranjay:Mo4MAznbTMcufpVAsU6Yzw@tailed-okapi-20468.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full"
    
    try:
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        collection_id = '0025c06b-d263-4398-a07a-582753cd89ed'
        
        print(f"--- Exploring Collection: Savoring 14th Street ---")
        
        # Join with restaurant_analysis to get name
        query = """
            SELECT ra.establishment, ci.restaurant_id
            FROM collection_items ci
            LEFT JOIN restaurant_analysis ra ON ci.restaurant_id::text = ra.id::text
            WHERE ci.collection_id = %s
        """
        cur.execute(query, (collection_id,))
        results = cur.fetchall()
        
        if not results:
            print("No restaurants found for this collection.")
        else:
            for i, r in enumerate(results, 1):
                name = r['establishment'] or "Unknown Name"
                print(f"{i}. {name} (ID: {r['restaurant_id']})")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    explore_collection()
