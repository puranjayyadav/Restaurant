-- Supabase RPC Function for Hybrid Fetch Strategy
-- This function efficiently fetches nearby saved places using PostGIS spatial indexing
-- Run this in your Supabase SQL Editor

-- First, ensure PostGIS extension is enabled
create extension if not exists postgis;

-- Create or replace the RPC function for getting nearby saved places
-- This assumes you have a 'places' table with lat/lng columns
-- If you're using 'yelp_restaurants', adjust the table name accordingly

-- Option 1: For a general 'places' table
create or replace function get_nearby_saved_places(
    lat float,
    lng float,
    radius_meters int default 2000
)
returns setof json
language sql
as $$
    select row_to_json(p.*)
    from places p
    where st_dwithin(
        st_setsrid(st_makepoint(lng, lat), 4326)::geography,
        st_setsrid(st_makepoint(p.lng, p.lat), 4326)::geography,
        radius_meters
    )
    and p.lat is not null
    and p.lng is not null;
$$;

-- Option 2: For 'yelp_restaurants' table (if that's your main places table)
-- Note: yelp_restaurants stores location as JSONB, so we need to extract it
create or replace function get_nearby_saved_places_yelp(
    lat float,
    lng float,
    radius_meters int default 2000
)
returns setof json
language sql
as $$
    select row_to_json(y.*)
    from yelp_restaurants y
    where y.location is not null
    and (y.location->>'lat')::float is not null
    and (y.location->>'lng')::float is not null
    and st_dwithin(
        st_setsrid(st_makepoint(lng, lat), 4326)::geography,
        st_setsrid(
            st_makepoint(
                (y.location->>'lng')::float,
                (y.location->>'lat')::float
            ),
            4326
        )::geography,
        radius_meters
    );
$$;

-- Option 3: For 'res_backend_scrapedrestaurant' table (Django model with OpenTable, etc.)
-- This table has latitude and longitude as numeric columns
create or replace function get_nearby_saved_places_scraped(
    lat float,
    lng float,
    radius_meters int default 2000
)
returns setof json
language sql
as $$
    select row_to_json(s.*)
    from res_backend_scrapedrestaurant s
    where s.latitude is not null
    and s.longitude is not null
    and s.is_active = true
    and s.duplicate_of_id is null  -- Only non-duplicate restaurants
    and st_dwithin(
        st_setsrid(st_makepoint(lng, lat), 4326)::geography,
        st_setsrid(st_makepoint(s.longitude::float, s.latitude::float), 4326)::geography,
        radius_meters
    );
$$;

-- Combined function: Fetches from all three sources (yelp_restaurants + res_backend_scrapedrestaurant)
-- This is the recommended function to use for hybrid fetch
create or replace function get_nearby_saved_places_all(
    lat float,
    lng float,
    radius_meters int default 2000
)
returns setof json
language plpgsql
as $$
begin
    -- Return yelp_restaurants
    return query
    select row_to_json(y.*) as result
    from yelp_restaurants y
    where y.location is not null
    and (y.location->>'lat')::float is not null
    and (y.location->>'lng')::float is not null
    and st_dwithin(
        st_setsrid(st_makepoint(lng, lat), 4326)::geography,
        st_setsrid(
            st_makepoint(
                (y.location->>'lng')::float,
                (y.location->>'lat')::float
            ),
            4326
        )::geography,
        radius_meters
    );
    
    -- Return scraped restaurants (OpenTable, etc.)
    return query
    select row_to_json(s.*) as result
    from res_backend_scrapedrestaurant s
    where s.latitude is not null
    and s.longitude is not null
    and s.is_active = true
    and s.duplicate_of_id is null
    and st_dwithin(
        st_setsrid(st_makepoint(lng, lat), 4326)::geography,
        st_setsrid(st_makepoint(s.longitude::float, s.latitude::float), 4326)::geography,
        radius_meters
    );
end;
$$;

-- Create spatial index for efficient queries (if using places table with lat/lng columns)
-- create index if not exists idx_places_location on places using gist(
--     st_setsrid(st_makepoint(lng, lat), 4326)::geography
-- );

-- For yelp_restaurants with JSONB location, create a functional index
-- create index if not exists idx_yelp_restaurants_location on yelp_restaurants using gist(
--     st_setsrid(
--         st_makepoint(
--             (location->>'lng')::float,
--             (location->>'lat')::float
--         ),
--         4326
--     )::geography
-- )
-- where location is not null
-- and (location->>'lat')::float is not null
-- and (location->>'lng')::float is not null;

-- For res_backend_scrapedrestaurant, create spatial index on latitude/longitude columns
-- create index if not exists idx_scrapedrestaurant_location on res_backend_scrapedrestaurant using gist(
--     st_setsrid(st_makepoint(longitude::float, latitude::float), 4326)::geography
-- )
-- where latitude is not null
-- and longitude is not null
-- and is_active = true
-- and duplicate_of_id is null;

