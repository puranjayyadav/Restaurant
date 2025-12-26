-- 1. Create the table to hold AI insights
-- ADAPTED: References 'venues' instead of 'places', and use TEXT for place_id to match Google Maps IDs
create table public.place_insights (
  id uuid primary key default gen_random_uuid(),
  place_id text references public.venues(place_id) on delete cascade not null, -- Links to your main Venues table
  
  -- HIGH-VALUE COLUMNS (Pull these out as real columns for fast filtering)
  display_short_name text,          -- "Drip"
  display_hook text,                -- "Flavor Bomb 💣"
  is_trap boolean default false,    -- Fast filter for "Don't show tourist traps"
  work_friendly boolean default false, -- Fast filter for "Digital Nomads"
  safety_flag boolean default false,   -- Fast filter for "Hide dangerous places"
  
  -- JSON DUMP (Store the complex nested stuff here)
  full_ai_json jsonb,               -- Stores the entire 'insider_profile' and 'benchmarks' object
  
  -- METADATA
  last_analyzed_at timestamptz default now(), -- So you know when to re-run the AI
  unique(place_id) -- Ensures 1 insight row per place
);

-- 2. Enable Row Level Security (RLS)
alter table public.place_insights enable row level security;

-- 3. Create a policy so your app can read it
create policy "Public places are viewable by everyone."
  on public.place_insights for select
  using ( true );
