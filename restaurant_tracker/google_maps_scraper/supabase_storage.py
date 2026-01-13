"""
Save scraped venues to Supabase with proper deduplication
Integrates with advanced_grid_scraper.py
"""

import os
from supabase import create_client
from decouple import config
from typing import List, Dict, Any

# Supabase Configuration
SUPABASE_URL = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
SUPABASE_KEY = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("Warning: Supabase credentials not found. Data will only be saved to JSON files.")
    supabase = None


def save_batch_to_supabase(results: List[Dict[str, Any]], vibe_slug: str, neighborhood: str) -> bool:
    """
    Saves scraped results to Supabase with deduplication.
    
    Two-step process:
    1. Upsert venues (deduplicated by place_id)
    2. Link venues to vibes (many-to-many relationship)
    
    Args:
        results: List of scraped place dictionaries
        vibe_slug: The vibe category (e.g., 'work_friendly')
        neighborhood: The neighborhood name (e.g., 'SoHo')
    
    Returns:
        True if successful, False otherwise
    """
    if not supabase:
        return False
    
    if not results:
        print("      [INFO] No results to save")
        return True
    
    # Prepare data for 'venues' table
    venues_data = []
    vibes_data = []
    
    for r in results:
        # Use place_id as primary key (Google's unique identifier)
        p_id = r.get('place_id')
        if not p_id:
            # Fallback: generate ID from name + address if place_id missing
            p_id = f"{r.get('name', 'unknown')}_{r.get('full_address', 'unknown')}".replace(' ', '_')
        
        # Prepare venue data
        venues_data.append({
            "place_id": p_id,
            "name": r.get('name'),
            "address": r.get('full_address'),
            "street_address": r.get('street_address'),
            "city": r.get('city'),
            "state": r.get('state'),
            "zip": r.get('zip'),
            "latitude": r.get('lat'),
            "longitude": r.get('long'),
            "rating": r.get('avg_rating'),
            "review_count": r.get('total_reviews'),
            "phone": r.get('phone'),
            "website": r.get('website'),
            "hours": r.get('hours'),  # JSON field
            "photos": r.get('photos'),  # JSON field
            "opentable_url": r.get('opentable_url'),
            "resy_url": r.get('resy_url'),
            "accepts_reservations": r.get('accepts_reservations', False)
        })
        
        # Prepare vibe association data
        vibes_data.append({
            "place_id": p_id,
            "vibe_slug": vibe_slug,
            "neighborhood": neighborhood
        })
    
    try:
        # STEP 1: Upsert venues
        # This will INSERT new venues or UPDATE existing ones
        print(f"      [INFO] Upserting {len(venues_data)} venues (deduplicating by place_id)...")
        venue_response = supabase.table("venues").upsert(
            venues_data,
            on_conflict="place_id"
        ).execute()
        
        # STEP 2: Upsert vibe associations
        # This creates the many-to-many relationship
        # If the same place+vibe combo exists, it won't create a duplicate
        print(f"      [INFO] Linking venues to vibe '{vibe_slug}' in '{neighborhood}'...")
        vibe_response = supabase.table("venue_vibes").upsert(
            vibes_data,
            on_conflict="place_id,vibe_slug"
        ).execute()
        
        print(f"      [SUCCESS] ✅ Saved {len(results)} venues (duplicates automatically merged)")
        print(f"      [INFO] Vibe associations: {len(vibes_data)} links created/updated")
        return True
        
    except Exception as e:
        print(f"      [ERROR] Supabase Error: {e}")
        return False


def save_hidden_gems_batch(results: List[Dict[str, Any]], vibe_slug: str, vibe_group: str, neighborhood: str, region: str) -> bool:
    """
    Saves scraped results specifically to the 'hidden_gems' table.
    """
    if not supabase:
        return False
    
    if not results:
        return True
    
    gems_data = []
    
    for r in results:
        p_id = r.get('place_id')
        if not p_id:
            p_id = f"{r.get('name', 'unknown')}_{r.get('full_address', 'unknown')}".replace(' ', '_')
        
        gems_data.append({
            "place_id": p_id,
            "name": r.get('name'),
            "address": r.get('full_address'),
            "street_address": r.get('street_address'),
            "city": r.get('city'),
            "state": r.get('state'),
            "zip": r.get('zip'),
            "latitude": r.get('lat'),
            "longitude": r.get('long'),
            "rating": r.get('avg_rating'),
            "review_count": r.get('total_reviews'),
            "phone": r.get('phone'),
            "website": r.get('website'),
            "hours": r.get('hours'),
            "photos": r.get('photos'),
            "vibe_slug": vibe_slug,
            "vibe_group": vibe_group,
            "neighborhood": neighborhood,
            "region": region
        })
    
    try:
        supabase.table("hidden_gems_v2").upsert(
            gems_data,
            on_conflict="place_id,vibe_slug,neighborhood"
        ).execute()
        
        print(f"      [SUPABASE] Synced {len(results)} gems to 'hidden_gems_v2' table")
        return True
    except Exception as e:
        print(f"      [SUPABASE ERROR] {e}")
        return False


def create_tables_if_not_exist():
    """
    Prints the SQL to create tables.
    Run this in your Supabase SQL Editor if tables don't exist yet.
    """
    sql = """
-- 1. Create the main venues table
CREATE TABLE IF NOT EXISTS venues (
  place_id TEXT PRIMARY KEY,
  name TEXT,
  address TEXT,
  street_address TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  latitude FLOAT,
  longitude FLOAT,
  rating FLOAT,
  review_count INT,
  phone TEXT,
  website TEXT,
  hours JSONB,
  photos JSONB,
  opentable_url TEXT,
  resy_url TEXT,
  accepts_reservations BOOLEAN DEFAULT FALSE,
  booking_platforms TEXT[],
  last_booking_check TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create the venue_vibes linking table
CREATE TABLE IF NOT EXISTS venue_vibes (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  place_id TEXT REFERENCES venues(place_id) ON DELETE CASCADE,
  vibe_slug TEXT,
  neighborhood TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Prevent duplicate vibe assignments
  UNIQUE(place_id, vibe_slug)
);

-- 3. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_venues_location ON venues(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_venues_rating ON venues(rating);
CREATE INDEX IF NOT EXISTS idx_venue_vibes_vibe ON venue_vibes(vibe_slug);
CREATE INDEX IF NOT EXISTS idx_venue_vibes_neighborhood ON venue_vibes(neighborhood);

-- 4. Enable Row Level Security (optional but recommended)
ALTER TABLE venues ENABLE ROW LEVEL SECURITY;
ALTER TABLE venue_vibes ENABLE ROW LEVEL SECURITY;

-- 5. Create policies (adjust based on your needs)
CREATE POLICY "Enable read access for all users" ON venues FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON venue_vibes FOR SELECT USING (true);
"""
    
    print("\n" + "="*60)
    print("  SUPABASE TABLE SETUP")
    print("="*60)
    print("\nRun this SQL in your Supabase SQL Editor:\n")
    print(sql)
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    # Print table creation SQL
    create_tables_if_not_exist()
    
    # Test connection
    if supabase:
        print("Supabase connection successful!")
        print(f"   URL: {SUPABASE_URL}")
    else:
        print("Supabase credentials not configured")
