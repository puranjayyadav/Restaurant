-- Migration to add booking columns to venues table
ALTER TABLE venues ADD COLUMN IF NOT EXISTS opentable_url TEXT;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS resy_url TEXT;
ALTER TABLE venues ADD COLUMN IF NOT EXISTS accepts_reservations BOOLEAN DEFAULT FALSE;

-- Ensure itineraries table exists (if not created by Supabase UI)
CREATE TABLE IF NOT EXISTS itineraries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id),
    title TEXT,
    query TEXT,
    chapters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS (Row Level Security) if not already enabled
ALTER TABLE itineraries ENABLE ROW LEVEL SECURITY;

-- Policy to allow anyone to read itineraries (or restrict as needed)
CREATE POLICY "Public itineraries are viewable by everyone" ON itineraries
    FOR SELECT USING (true);

-- Policy to allow authenticated users to insert their own itineraries
CREATE POLICY "Users can insert their own itineraries" ON itineraries
    FOR INSERT WITH CHECK (auth.uid() = user_id);
