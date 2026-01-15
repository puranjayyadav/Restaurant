import os
import subprocess
import json
import time
from supabase import create_client
from decouple import config

# Supabase Configuration
SUPABASE_URL = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
SUPABASE_KEY = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in environment or .env file.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def update_venue_stats(max_venues=10):
    print(f"🔍 Fetching up to {max_venues} venues to sync...")
    
    # Fetch venues where we haven't checked business status recently or at all
    # We'll use review_count as a proxy if business_status column doesn't exist yet,
    # but let's try to just get the records first.
    try:
        response = supabase.table("venues").select("place_id, name, review_count").limit(max_venues).execute()
        venues = response.data
    except Exception as e:
        print(f"❌ Error fetching venues: {e}")
        return

    if not venues:
        print("✅ No venues found to update.")
        return

    scraper_path = os.path.join(os.path.dirname(__file__), "review_scraper_test", "venue_status_scraper.js")

    for venue in venues:
        pid = venue['place_id']
        name = venue['name']
        print(f"\n🏷️  Processing: {name} ({pid})")

        try:
            # Run the Node.js scraper
            result = subprocess.run(
                ["node", scraper_path, pid],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                if "error" in data:
                    print(f"   ⚠️  Scraper error: {data['error']}")
                    continue

                print(f"   📊 Reviews: {data.get('review_count')} | Status: {data.get('business_status')}")

                # Prepare update payload
                update_data = {
                    "review_count": data.get('review_count'),
                    "business_status": data.get('business_status'),
                    "price_range": data.get('price_range'),
                    "updated_at": "now()" 
                }

                # Update Supabase
                supabase.table("venues").update(update_data).eq("place_id", pid).execute()
                
                # Update Hours
                hours = data.get('hours', [])
                if hours:
                    hours_payload = []
                    for h in hours:
                        hours_payload.append({
                            "place_id": pid,
                            "day": h['day'],
                            "hours": h['hours']
                        })
                    supabase.table("venue_hours").upsert(hours_payload, on_conflict="place_id,day").execute()
                    print(f"   ⏰ Synced {len(hours)} hours records.")

                print(f"   ✅ Successfully updated in database.")

            else:
                print(f"   ❌ Node process failed: {result.stderr}")

        except Exception as e:
            print(f"   ❌ Error processing {name}: {e}")

        # Rate limiting to avoid Google blocks
        time.sleep(5)

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    update_venue_stats(limit)
