# Lemon8 Snowball Crawler

A zero-cost, production-ready scraping pipeline for Lemon8 that uses Supabase as a queue and GitHub Actions for free automation.

## Architecture

**Scout (Discovery)**: Finds post URLs from hashtags and influencers, adds them to Supabase queue  
**Miner (Processor)**: Takes URLs from queue, scrapes HTML, runs LLM extraction, saves to Supabase

## Setup

### 1. Supabase Database

1. Create a new Supabase project at https://supabase.com
2. Go to SQL Editor and run `supabase_schema.sql`
3. Get your project URL and anon key from Settings > API

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. GitHub Actions (Free Automation)

1. Push this code to a GitHub repository
2. Go to Settings > Secrets and variables > Actions
3. Add these secrets:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `OPENROUTER_API_KEY`
4. The workflow will automatically run:
   - **Scout**: Every 6 hours (discovers new URLs)
   - **Miner**: Every 2 hours (processes queue)

## Local Usage

### Run Scout (Discover URLs)

```bash
python scout_lemon8.py "https://www.lemon8-app.com/experience/new-york-eat?region=us"
```

You can pass multiple seed URLs:
```bash
python scout_lemon8.py "https://..." "https://..." "https://..."
```

### Run Miner (Process Queue)

```bash
python miner_lemon8.py 10  # Process 10 URLs
```

## How It Works

1. **Scout** visits seed URLs (hashtags, influencer pages), auto-scrolls to load content, extracts article links
2. URLs are added to `crawl_queue` table in Supabase (duplicates are automatically skipped)
3. **Miner** fetches pending URLs from queue, processes them:
   - Scrapes HTML content from `<section id="article-content">`
   - Extracts structured itinerary data using free LLM models (OpenRouter)
   - Saves everything to `lemon8_articles` table
4. Queue status is tracked: `pending` → `processing` → `completed`/`failed`

## Database Schema

### `crawl_queue`
- `url` (primary key)
- `status`: pending, processing, completed, failed
- `source_hashtag`, `source_url`: Where URL was discovered
- `discovered_at`, `processed_at`: Timestamps
- `retry_count`: Automatic retry logic

### `lemon8_articles`
- `url` (primary key)
- `html_content`: Scraped HTML
- `itinerary_data`: JSONB with extracted data
- `scraped_at`, `extracted_at`: Timestamps

## Rate Limiting & Safety

- **Scout**: 2 second delay between seed URLs
- **Miner**: 3 second delay between article URLs
- Automatic retry logic (max 3 retries)
- Headless browser mode for automation
- Respectful user-agent strings

## Monitoring

Check queue stats:
```python
from supabase_config import get_queue_stats
stats = get_queue_stats()
print(stats)
```

## Cost

- **Supabase**: Free tier (500MB database, 2GB bandwidth)
- **GitHub Actions**: Free tier (2000 minutes/month)
- **OpenRouter**: Free tier (50-1000 requests/day depending on credits)
- **Total**: $0/month for moderate usage

## Troubleshooting

### Scout not finding URLs
- Check if Lemon8 page structure changed
- Increase `max_scrolls` in `scout_lemon8.py`
- Verify Brave/Chrome is installed

### Miner failing
- Check Supabase connection (URL and key)
- Verify OpenRouter API key
- Check browser logs for errors

### GitHub Actions failing
- Verify all secrets are set correctly
- Check Actions logs for specific errors
- Ensure Python dependencies are in `requirements.txt`
