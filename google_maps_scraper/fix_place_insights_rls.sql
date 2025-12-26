-- The previous policy only allowed SELECT. 
-- We need to allow INSERT and UPDATE so the script can save insights.

-- 1. Drop the old policy (if it exists, though 'create policy' might error if duplicate names, better to drop first)
drop policy if exists "Public places are viewable by everyone." on public.place_insights;

-- 2. Create a permissive policy for development
-- check (true) is needed for INSERT/UPDATE
create policy "Enable full access for all users"
  on public.place_insights
  for all
  using ( true )
  with check ( true );
