import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_schema():
    conn_string = os.getenv("COCKROACHDB_URL")
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("Columns in collections:")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'collections'")
    print(cur.fetchall())
    
    print("\nColumns in collection_items:")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'collection_items'")
    print(cur.fetchall())
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_schema()
