-- Snowball Crawler Database Schema for Lemon8 Scraping
-- Run this in your Supabase SQL Editor

-- Queue table to manage discovered URLs
create table if not exists crawl_queue (
  url text primary key,
  source_hashtag text,
  source_url text, -- The page where this URL was discovered
  status text default 'pending', -- 'pending', 'processing', 'completed', 'failed'
  discovered_at timestamp default now(),
  processed_at timestamp,
  error_message text,
  retry_count integer default 0,
  max_retries integer default 3
);

-- Index for fast lookup of pending jobs
create index if not exists idx_queue_status on crawl_queue(status);
create index if not exists idx_queue_discovered on crawl_queue(discovered_at);

-- Articles table to store scraped content and extracted data
create table if not exists lemon8_articles (
  url text primary key,
  html_content text,
  itinerary_data jsonb,
  enriched_itinerary_data jsonb,
  stops_lat double precision[],
  stops_lng double precision[],
  scraped_at timestamp default now(),
  extracted_at timestamp,
  extraction_error text,
  created_at timestamp default now(),
  updated_at timestamp default now()
);

-- Index for searching itinerary data
create index if not exists idx_articles_extracted on lemon8_articles(extracted_at);
create index if not exists idx_articles_created on lemon8_articles(created_at);

-- Function to update updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Trigger to auto-update updated_at
create trigger update_lemon8_articles_updated_at
  before update on lemon8_articles
  for each row
  execute function update_updated_at_column();

-- Yelp URL Queue table
create table if not exists crawl_queue_yelp (
  yelp_id text primary key,
  url text not null,
  place_name text,
  city text,
  lemon8_source jsonb, -- Stores the original restaurant data from Lemon8 article
  status text default 'pending', -- 'pending', 'processing', 'completed', 'failed'
  discovered_at timestamp default now(),
  processed_at timestamp,
  error_message text,
  retry_count integer default 0,
  max_retries integer default 3
);

-- Index for fast lookup
create index if not exists idx_yelp_queue_status on crawl_queue_yelp(status);
create index if not exists idx_yelp_queue_discovered on crawl_queue_yelp(discovered_at);
create index if not exists idx_yelp_queue_city on crawl_queue_yelp(city);

-- Yelp Restaurants table to store scraped restaurant data
create table if not exists yelp_restaurants (
  yelp_id text primary key,
  source text default 'yelp',
  source_id text,
  source_url text,
  url text not null,
  name text,
  description text,
  address text,
  city text,
  state text,
  rating numeric,
  total_reviews integer,
  review_count integer,
  price_range text,
  phone text,
  website text,
  hours jsonb,
  categories text[],
  cuisine text,
  photos text[],
  images text[],
  image_urls text[],
  supabase_photos text[],  -- Supabase Storage URLs
  supabase_image_urls text[],  -- Supabase Storage URLs (alias)
  supabase_images text[],  -- Supabase Storage URLs (alias)
  header_image_url text,  -- Best header image URL (selected by HeaderSelector)
  menu_items jsonb,
  popular_dishes jsonb,
  reviews jsonb,
  menu_link text,
  amenities text[],
  location jsonb,
  lemon8_source jsonb,
  scraped_at timestamp default now(),
  created_at timestamp default now(),
  updated_at timestamp default now()
);

-- Index for searching
create index if not exists idx_yelp_restaurants_city on yelp_restaurants(city);
create index if not exists idx_yelp_restaurants_rating on yelp_restaurants(rating);
create index if not exists idx_yelp_restaurants_scraped on yelp_restaurants(scraped_at);

-- Trigger to auto-update updated_at
create trigger update_yelp_restaurants_updated_at
  before update on yelp_restaurants
  for each row
  execute function update_updated_at_column();