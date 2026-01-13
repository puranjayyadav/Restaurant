-- PostGIS Neighborhood Cluster Function for NBA Solver
-- Run this in your Supabase SQL Editor

DROP FUNCTION IF EXISTS get_neighborhood_cluster(float, float, float);

CREATE OR REPLACE FUNCTION get_neighborhood_cluster(
  center_lat float, 
  center_lng float, 
  radius_meters float DEFAULT 1500
)
RETURNS TABLE (
  id bigint,
  name varchar,
  rating decimal,
  user_ratings_total int,
  vibe_tags jsonb,
  categories jsonb,
  lat float,
  lng float,
  distance_m float,
  notes text
) 
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    p.id, 
    p.name, 
    p.rating, 
    p.total_reviews as user_ratings_total,
    p.raw_data->'vibe_tags' as vibe_tags,
    p.categories,
    p.latitude::float as lat,
    p.longitude::float as lng,
    ST_Distance(
      ST_SetSRID(ST_Point(p.longitude, p.latitude), 4326)::geography,
      ST_SetSRID(ST_Point(center_lng, center_lat), 4326)::geography
    ) as distance_m,
    p.description as notes
  FROM res_backend_scrapedrestaurant p
  WHERE ST_DWithin(
    ST_SetSRID(ST_Point(p.longitude, p.latitude), 4326)::geography, 
    ST_SetSRID(ST_Point(center_lng, center_lat), 4326)::geography, 
    radius_meters
  )
  AND p.is_active = true
  ORDER BY p.rating DESC, p.total_reviews DESC
  LIMIT 100;
END;
$$;

-- NOTE: This function requires:
-- 1. PostGIS extension enabled: CREATE EXTENSION IF NOT EXISTS postgis;
-- 2. A 'places' table with a 'location' column of type GEOGRAPHY(Point, 4326)
-- 3. If your table uses separate lat/lng columns, modify the query accordingly
