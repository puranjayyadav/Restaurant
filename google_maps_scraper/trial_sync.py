import os
import subprocess
import json
from supabase import create_client
from decouple import config

# Supabase Configuration
SUPABASE_URL = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
SUPABASE_KEY = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def trial_run(pid):
    scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "review_scraper_test", "venue_status_scraper.js"))
    
    # Force UTF-8 environment and encoding for Windows compatibility
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    result = subprocess.run(
        ["node", scraper_path, pid],
        capture_output=True,
        text=True,
        timeout=60,
        shell=True,
        encoding="utf-8",
        env=env
    )
    
    if result.returncode == 0:
        data = json.loads(result.stdout)
        print(f"✅ Scraped Data: {data}")
        
        update_data = {
            "review_count": data.get('review_count'),
            "business_status": data.get('business_status'),
            "updated_at": "now"
        }
        
        if data.get('price_range'):
            update_data["price_range"] = data.get('price_range')
        
        print(f"📊 Updating DB with: {update_data}")
        res = supabase.table("venues").update(update_data).eq("place_id", pid).execute()
        
        # Update Hours
        hours = data.get('hours', [])
        if hours:
            print(f"⏰ Syncing {len(hours)} hours records...")
            hours_payload = []
            for h in hours:
                hours_payload.append({
                    "place_id": pid,
                    "day": h['day'],
                    "hours": h['hours']
                })
            
            # Use upsert to prevent duplicates
            supabase.table("venue_hours").upsert(hours_payload, on_conflict="place_id,day").execute()
            print("✅ Hours synced.")
            
        print(f"🎉 Database Update Result: Success")
    else:
        print(f"❌ Error: {result.stderr}")

if __name__ == "__main__":
    trial_run("ChIJyVUVFb9ZwokRWcd_vzEwRsM")
