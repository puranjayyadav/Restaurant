import psycopg2
import os

def add_columns():
    # Retrieve connection string from environment variable
    conn_string = os.environ.get('COCKROACHDB_URL')
    if not conn_string:
        print("Error: COCKROACHDB_URL environment variable not set.")
        return

    try:
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor()

        print("Checking for latitude/longitude columns in restaurant_analysis...")

        # Check if columns exist
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'restaurant_analysis' AND column_name IN ('latitude', 'longitude');
        """)
        existing_columns = [row[0] for row in cur.fetchall()]

        if 'latitude' not in existing_columns:
            print("Adding latitude column...")
            cur.execute("ALTER TABLE restaurant_analysis ADD COLUMN latitude DOUBLE PRECISION;")
        else:
            print("latitude column already exists.")

        if 'longitude' not in existing_columns:
            print("Adding longitude column...")
            cur.execute("ALTER TABLE restaurant_analysis ADD COLUMN longitude DOUBLE PRECISION;")
        else:
            print("longitude column already exists.")

        conn.commit()
        print("Schema update complete.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating schema: {e}")

if __name__ == "__main__":
    add_columns()
