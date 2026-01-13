-- Fix Supabase permissions for INSERT/UPDATE operations
-- Run this in your Supabase SQL Editor

-- Drop existing policies
DROP POLICY IF EXISTS "Enable read access for all users" ON venues;
DROP POLICY IF EXISTS "Enable read access for all users" ON venue_vibes;

-- Create comprehensive policies for venues table
CREATE POLICY "Enable all operations for service role" 
ON venues FOR ALL 
USING (true) 
WITH CHECK (true);

-- Create comprehensive policies for venue_vibes table
CREATE POLICY "Enable all operations for service role" 
ON venue_vibes FOR ALL 
USING (true) 
WITH CHECK (true);

-- Alternatively, if you want to disable RLS for now (simpler for development):
-- ALTER TABLE venues DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE venue_vibes DISABLE ROW LEVEL SECURITY;
