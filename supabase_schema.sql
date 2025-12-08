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
