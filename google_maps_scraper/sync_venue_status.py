# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import json
import time
from supabase import create_client
from decouple import config

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Supabase Configuration
SUPABASE_URL = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
SUPABASE_KEY = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in environment or .env file.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

from datetime import datetime, timedelta, timezone

def update_venue_stats(batch_size=10, skip_recent_days=7):
    # Calculate the cutoff date in Python
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=skip_recent_days)).isoformat()
    
    print(f"� Starting continuous sync (batch size: {batch_size})")
    print(f"   (Skipping venues updated after {cutoff_date})")
    
    total_processed = 0
    processed_ids = set() # Track IDs to avoid infinite loops on failed records
    scraper_path = os.path.join(os.path.dirname(__file__), "review_scraper_test", "venue_status_scraper.js")

    while True:
        try:
            # Fetch venues that either have no status OR haven't been updated since the cutoff
            query = supabase.table("venues").select("place_id, name, review_count, business_status, updated_at")
            
            # Filter out IDs we've already attempted in this session to avoid loops
            response = query.or_(f"business_status.is.null,updated_at.lt.{cutoff_date}").limit(batch_size).execute()
            venues = response.data
            
            # Filter out already tried IDs in Python (since .not.in_ is tricky with many IDs)
            venues = [v for v in venues if v['place_id'] not in processed_ids]
            
            if not venues:
                print(f"\n✨ COMPLETED: No more unprocessed venues found.")
                print(f"🎉 Total venues processed in this session: {total_processed}")
                break
                
            print(f"\n📦 Next Batch: {len(venues)} venues (Total processed so far: {total_processed})")
        except Exception as e:
            print(f"❌ Error fetching venues: {e}")
            break

        for venue in venues:
            pid = venue['place_id']
            name = venue['name']
            processed_ids.add(pid)
            total_processed += 1
            
            print(f"\n🏷️  [{total_processed}] Processing: {name} ({pid})")

            try:
                # Run the Node.js scraper
                result = subprocess.run(
                    ["node", scraper_path, pid],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
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
                        "updated_at": datetime.now(timezone.utc).isoformat()
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
    skip_days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(f"📋 Running with limit={limit}, skip_recent_days={skip_days}")
    update_venue_stats(limit, skip_days)
