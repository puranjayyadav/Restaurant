-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to venues
ALTER TABLE venues ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE venues ADD COLUMN IF NOT EXISTS embedding_updated_at TIMESTAMP WITH TIME ZONE;

-- Create index for fast similarity search
-- Note: ivfflat requires at least 100 rows, so we'll create it conditionally or use a simpler index
-- For now, create a basic index that works with any number of rows
CREATE INDEX IF NOT EXISTS idx_venues_embedding ON venues USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- Create hybrid search function
CREATE OR REPLACE FUNCTION hybrid_search_venues(
  query_embedding vector(1536),
  vibe_slugs text[],
  cuisine_slugs text[],
  match_threshold float DEFAULT 0.3,
  lat float DEFAULT NULL,
  lng float DEFAULT NULL,
  radius_km float DEFAULT 5.0,
  limit_count int DEFAULT 50
)
RETURNS TABLE (
  place_id text,
  name text,
  address text,
  latitude float,
  longitude float,
  rating float,
  review_count int,
  semantic_score float,
  vibe_match_score float,
  insight_score float,
  final_score float,
  matched_vibes text[],
  display_hook text,
  must_order jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH semantic_matches AS (
    SELECT 
      v.place_id,
      v.name,
      v.address,
      v.latitude,
      v.longitude,
      v.rating,
      v.review_count,
      (1 - (v.embedding <=> query_embedding)) as similarity,
      -- Check if venue has cuisine match (for later filtering/boosting)
      CASE 
        WHEN array_length(cuisine_slugs, 1) > 0 THEN
          EXISTS (
            SELECT 1 
            FROM venue_vibes vv 
            WHERE vv.place_id = v.place_id 
            AND vv.vibe_slug = ANY(cuisine_slugs)
          )
        ELSE false
      END as has_cuisine_match
    FROM venues v
    WHERE v.embedding IS NOT NULL
      AND (1 - (v.embedding <=> query_embedding)) > match_threshold
      AND (lat IS NULL OR (
        -- Distance filter using haversine
        6371 * acos(
          cos(radians(lat)) * cos(radians(v.latitude)) * 
          cos(radians(v.longitude) - radians(lng)) + 
          sin(radians(lat)) * sin(radians(v.latitude))
        ) <= radius_km
      ))
    ORDER BY v.embedding <=> query_embedding
    LIMIT 200
  ),
  vibe_enriched AS (
    SELECT 
      sm.*,
      COALESCE(array_agg(DISTINCT vv.vibe_slug) FILTER (WHERE vv.vibe_slug IS NOT NULL), '{}') as venue_vibes,
      -- Calculate vibe match score (cast to float)
      CASE 
        WHEN array_length(vibe_slugs, 1) > 0 OR array_length(cuisine_slugs, 1) > 0 THEN
          GREATEST(
            COALESCE(
              (SELECT COUNT(*)::float / GREATEST(array_length(vibe_slugs, 1), 1)::float
               FROM unnest(vibe_slugs) vs
               WHERE vs = ANY(array_agg(vv.vibe_slug))), 
              0.0::float
            ),
            COALESCE(
              (SELECT COUNT(*)::float / GREATEST(array_length(cuisine_slugs, 1), 1)::float
               FROM unnest(cuisine_slugs) cs
               WHERE cs = ANY(array_agg(vv.vibe_slug))), 
              0.0::float
            )
          )::float
        ELSE 0.5::float
      END as vibe_score
    FROM semantic_matches sm
    LEFT JOIN venue_vibes vv ON sm.place_id = vv.place_id
    GROUP BY sm.place_id, sm.name, sm.address, sm.latitude, sm.longitude, 
             sm.rating, sm.review_count, sm.similarity, sm.has_cuisine_match
  ),
  cuisine_filtered AS (
    -- Pass through all venues - we'll boost cuisine matches in scoring instead of filtering
    -- This ensures we always return results, but prioritize cuisine matches when they exist
    SELECT ve.*
    FROM vibe_enriched ve
  ),
  insight_enriched AS (
    SELECT 
      cf.*,
      pi.display_hook,
      pi.full_ai_json->'insider_profile'->'must_order' as must_order_items,
      -- Calculate insight score (cast to float)
      (
        CASE WHEN pi.is_trap THEN -0.3::float ELSE 0.0::float END +
        CASE WHEN pi.safety_flag THEN -0.5::float ELSE 0.0::float END +
        CASE WHEN (pi.full_ai_json->'plandit_benchmarks'->>'date_night_score')::boolean AND 'dinner_date' = ANY(vibe_slugs) THEN 0.2::float ELSE 0.0::float END +
        CASE WHEN pi.work_friendly AND 'work_friendly' = ANY(vibe_slugs) THEN 0.2::float ELSE 0.0::float END +
        CASE WHEN (pi.full_ai_json->'plandit_benchmarks'->>'grandma_approval')::boolean THEN 0.15::float ELSE 0.0::float END +
        CASE WHEN cf.rating >= 4.5 THEN 0.1::float ELSE 0.0::float END
      )::float as insight_bonus
    FROM cuisine_filtered cf
    LEFT JOIN place_insights pi ON cf.place_id = pi.place_id
  )
  SELECT 
    ie.place_id,
    ie.name,
    ie.address,
    ie.latitude,
    ie.longitude,
    ie.rating,
    ie.review_count,
    ie.similarity::float as semantic_score,
    ie.vibe_score::float as vibe_match_score,
    ie.insight_bonus::float as insight_score,
    -- Weighted final score: 60% semantic + 25% vibe + 15% insights
    -- Strongly boost cuisine matches (when cuisine_slugs provided) to prioritize them
    (
      ie.similarity::float * 0.6::float + 
      ie.vibe_score::float * 0.25::float + 
      GREATEST(ie.insight_bonus::float, 0.0::float) * 0.15::float +
      CASE 
        WHEN array_length(cuisine_slugs, 1) > 0 AND 
             EXISTS (SELECT 1 FROM unnest(ie.venue_vibes) v WHERE v = ANY(cuisine_slugs))
        THEN 0.5::float  -- Very strong boost for cuisine matches to ensure they rank at top
        ELSE 0.0::float
      END
    )::float as final_score,
    ie.venue_vibes as matched_vibes,
    ie.display_hook,
    ie.must_order_items as must_order
  FROM insight_enriched ie
  ORDER BY final_score DESC
  LIMIT limit_count;
END;
$$;
