import psycopg2
import time
import sys
import random
import os
from psycopg2.extras import RealDictCursor
from google_maps_scraper import search_place_by_name

def get_connection():
    conn_string = os.environ.get('COCKROACHDB_URL')
    if not conn_string:
        raise ValueError("COCKROACHDB_URL environment variable not set.")
    return psycopg2.connect(conn_string)

def geocode_rows():
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Fetch rows that need geocoding
        cur.execute("SELECT id, establishment, neighborhood FROM restaurant_analysis WHERE latitude IS NULL")
        rows = cur.fetchall()
        print(f"Found {len(rows)} rows to geocode.")

        for i, row in enumerate(rows):
            establishment = row['establishment']
            neighborhood = row['neighborhood']
            row_id = row['id']

            # Skip if establishment is explicitly "None" or similar
            if not establishment or "None (no specific establishment" in establishment:
                print(f"Skipping invalid establishment: {establishment}")
                continue

            # Construct search query
            query_parts = [establishment]

            # Add neighborhood if valid
            if neighborhood and neighborhood.lower() not in ['not mentioned', 'n/a', 'null', 'none']:
                query_parts.append(neighborhood)

            # Always add NYC context since user specified "all of these places are within NYC"
            query_parts.append("NYC")

            search_query = " ".join(query_parts)
            print(f"[{i+1}/{len(rows)}] Searching for: {search_query}")

            try:
                # Use the scraper
                # search_place_by_name is good for specific places
                result = search_place_by_name(search_query)

                if result and result.get('lat') and result.get('lon'):
                    lat = result['lat']
                    lon = result['lon']
                    print(f"  -> Found: {lat}, {lon} ({result.get('address')})")

                    # Update database
                    update_cur = conn.cursor()
                    update_cur.execute(
                        "UPDATE restaurant_analysis SET latitude = %s, longitude = %s WHERE id = %s",
                        (lat, lon, row_id)
                    )
                    conn.commit()
                    update_cur.close()
                else:
                    print(f"  -> Not found.")

            except Exception as e:
                print(f"  -> Error geocoding {search_query}: {e}")

            # Sleep to be polite to Google
            sleep_time = random.uniform(2, 5)
            time.sleep(sleep_time)

    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    geocode_rows()
