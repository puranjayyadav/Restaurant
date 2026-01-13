-- Optimized version of hybrid_search_venues function
-- This version is simpler and faster, avoiding expensive operations

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
      (1 - (v.embedding <=> query_embedding))::float as similarity
    FROM venues v
    WHERE v.embedding IS NOT NULL
      AND (1 - (v.embedding <=> query_embedding)) > match_threshold
      AND (lat IS NULL OR lng IS NULL OR (
        -- Simplified distance check (avoid expensive haversine in WHERE clause)
        ABS(v.latitude - lat) < (radius_km / 111.0)  -- Rough km to degrees
        AND ABS(v.longitude - lng) < (radius_km / (111.0 * COS(RADIANS(lat))))
      ))
    ORDER BY v.embedding <=> query_embedding
    LIMIT 100  -- Reduced from 200
  ),
  vibe_enriched AS (
    SELECT 
      sm.*,
      COALESCE(
        (SELECT array_agg(DISTINCT vv.vibe_slug) 
         FROM venue_vibes vv 
         WHERE vv.place_id = sm.place_id 
         AND vv.vibe_slug IS NOT NULL),
        '{}'::text[]
      ) as venue_vibes,
      -- Simplified vibe score calculation
      CASE 
        WHEN array_length(vibe_slugs, 1) > 0 OR array_length(cuisine_slugs, 1) > 0 THEN
          COALESCE(
            (SELECT COUNT(*)::float / GREATEST(array_length(vibe_slugs, 1), 1)::float
             FROM unnest(vibe_slugs) vs
             WHERE vs = ANY(
               (SELECT array_agg(vv.vibe_slug) 
                FROM venue_vibes vv 
                WHERE vv.place_id = sm.place_id)
             )),
            0.0::float
          )
        ELSE 0.5::float
      END::float as vibe_score
    FROM semantic_matches sm
  ),
  insight_enriched AS (
    SELECT 
      ve.*,
      pi.display_hook,
      pi.full_ai_json->'insider_profile'->'must_order' as must_order_items,
      -- Simplified insight score
      COALESCE(
        (CASE WHEN pi.is_trap THEN -0.3::float ELSE 0.0::float END +
         CASE WHEN pi.safety_flag THEN -0.5::float ELSE 0.0::float END +
         CASE WHEN (pi.full_ai_json->'plandit_benchmarks'->>'date_night_score')::boolean 
              AND 'dinner_date' = ANY(vibe_slugs) THEN 0.2::float ELSE 0.0::float END +
         CASE WHEN pi.work_friendly AND 'work_friendly' = ANY(vibe_slugs) THEN 0.2::float ELSE 0.0::float END +
         CASE WHEN (pi.full_ai_json->'plandit_benchmarks'->>'grandma_approval')::boolean THEN 0.15::float ELSE 0.0::float END +
         CASE WHEN ve.rating >= 4.5 THEN 0.1::float ELSE 0.0::float END),
        0.0::float
      )::float as insight_bonus
    FROM vibe_enriched ve
    LEFT JOIN place_insights pi ON ve.place_id = pi.place_id
  )
  SELECT 
    ie.place_id,
    ie.name,
    ie.address,
    ie.latitude,
    ie.longitude,
    ie.rating,
    ie.review_count,
    ie.similarity as semantic_score,
    ie.vibe_score as vibe_match_score,
    ie.insight_bonus as insight_score,
    -- Weighted final score: 60% semantic + 25% vibe + 15% insights
    (ie.similarity * 0.6 + ie.vibe_score * 0.25 + GREATEST(ie.insight_bonus, 0.0) * 0.15)::float as final_score,
    ie.venue_vibes as matched_vibes,
    ie.display_hook,
    ie.must_order_items as must_order
  FROM insight_enriched ie
  ORDER BY final_score DESC
  LIMIT limit_count;
END;
$$;
