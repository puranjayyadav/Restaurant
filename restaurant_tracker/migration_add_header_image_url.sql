-- Migration: Add header_image_url column to yelp_restaurants table
-- Run this in your Supabase SQL Editor if the column doesn't exist yet

-- Add header_image_url column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'yelp_restaurants' 
        AND column_name = 'header_image_url'
    ) THEN
        ALTER TABLE yelp_restaurants 
        ADD COLUMN header_image_url text;
        
        RAISE NOTICE 'Column header_image_url added successfully';
    ELSE
        RAISE NOTICE 'Column header_image_url already exists';
    END IF;
END $$;

-- Optional: Create an index for faster lookups
CREATE INDEX IF NOT EXISTS idx_yelp_restaurants_header_image 
ON yelp_restaurants(header_image_url) 
WHERE header_image_url IS NOT NULL;

