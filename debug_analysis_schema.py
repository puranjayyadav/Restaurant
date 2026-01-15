import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_analysis():
    conn_string = "postgresql://puranjay:Mo4MAznbTMcufpVAsU6Yzw@tailed-okapi-20468.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full"
    
    try:
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM restaurant_analysis LIMIT 1")
        row = cur.fetchone()
        if row:
            print("Columns in restaurant_analysis:")
            print(list(row.keys()))
            print("\nSample Data:")
            print(row)
        else:
            print("Table restaurant_analysis is empty.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_analysis()
