# Snowball Crawler Architecture

## Overview

The Snowball Crawler is a zero-cost, production-ready scraping pipeline that uses:
- **Supabase** as the queue and database (free tier)
- **GitHub Actions** for free automation (2000 minutes/month)
- **OpenRouter** for free LLM extraction (50-1000 requests/day)

## Components

### 1. Database (Supabase)

**`crawl_queue` table:**
- Manages discovered URLs
- Tracks status: `pending` → `processing` → `completed`/`failed`
- Prevents duplicate scraping
- Automatic retry logic (max 3 retries)

**`lemon8_articles` table:**
- Stores scraped HTML content
- Stores extracted itinerary data (JSONB)
- Tracks timestamps for scraping and extraction

### 2. Scout (`scout_lemon8.py`)

**Purpose:** Discovers new article URLs

**Process:**
1. Visits seed URLs (hashtags, influencer pages)
2. Auto-scrolls to load dynamic content
3. Extracts article links from `<a class="article-recommend-card">`
4. Adds unique URLs to `crawl_queue` (skips duplicates)

**Usage:**
```bash
python scout_lemon8.py "https://www.lemon8-app.com/experience/new-york-eat?region=us"
```

**Features:**
- Headless browser mode
- Rate limiting (2s delay between seed URLs)
- Automatic duplicate detection
- Queue statistics

### 3. Miner (`miner_lemon8.py`)

**Purpose:** Processes queue, scrapes content, extracts data

**Process:**
1. Fetches pending URLs from `crawl_queue`
2. Marks URL as `processing`
3. Scrapes HTML from `<section id="article-content">`
4. Extracts structured data using free LLM models
5. Saves to `lemon8_articles` table
6. Marks URL as `completed` or `failed`

**Usage:**
```bash
python miner_lemon8.py 10  # Process 10 URLs
```

**Features:**
- Batch processing
- Automatic retry on failure
- LLM extraction with multiple free model fallbacks
- Rate limiting (3s delay between URLs)

### 4. LLM Extraction (`extract_itineraries_from_articles.py`)

**Purpose:** Extract structured itinerary data from HTML

**Process:**
1. Truncates HTML to 10k characters (token limits)
2. Tries multiple free OpenRouter models in order
3. Handles rate limits (429) by waiting and trying next model
4. Parses JSON response
5. Returns structured data: `{itinerary_title, city, stops: [...]}`

**Free Models Used:**
- `meta-llama/llama-3.2-3b-instruct:free`
- `tngtech/deepseek-r1t2-chimera:free`
- `kwaipilot/kat-coder-pro:free`
- ... and 9 more fallback models

### 5. Automation (GitHub Actions)

**Workflow:** `.github/workflows/lemon8_crawler.yml`

**Schedule:**
- **Scout**: Every 6 hours (discovers new URLs)
- **Miner**: Every 2 hours (processes queue)

**Manual Trigger:** Available via GitHub Actions UI

## Data Flow

```
Seed URLs → Scout → crawl_queue (pending)
                        ↓
                   Miner (fetches pending)
                        ↓
              Scrape HTML → Extract with LLM
                        ↓
              lemon8_articles (completed)
```

## Rate Limiting Strategy

1. **Scout**: 2 second delay between seed URLs
2. **Miner**: 3 second delay between article URLs
3. **LLM**: Automatic fallback to next model on rate limit
4. **Retry Logic**: Max 3 retries with exponential backoff

## Cost Breakdown

| Service | Free Tier | Usage |
|---------|-----------|-------|
| Supabase | 500MB DB, 2GB bandwidth | Queue + Articles |
| GitHub Actions | 2000 min/month | ~240 min/month (6h scout + 2h miner) |
| OpenRouter | 50-1000 req/day | ~10-50 articles/day |

**Total Monthly Cost: $0**

## Monitoring

### Queue Stats
```python
from supabase_config import get_queue_stats
stats = get_queue_stats()
# Returns: {pending, processing, completed, failed}
```

### Supabase Dashboard
- View `crawl_queue` table for queue status
- View `lemon8_articles` table for scraped data
- Monitor database size and bandwidth

### GitHub Actions
- View workflow runs in Actions tab
- Check logs for errors
- Manual trigger for testing

## Scaling

**To increase throughput:**
1. Add more seed URLs to Scout
2. Increase Miner batch size
3. Run Miner more frequently (adjust cron schedule)
4. Add more GitHub Actions workflows (if within free tier)

**To reduce costs:**
1. Reduce Scout frequency (every 12h instead of 6h)
2. Reduce Miner batch size
3. Increase delays between requests

## Security

- API keys stored as GitHub Secrets
- Supabase RLS (Row Level Security) can be enabled
- No sensitive data in code
- Headless browser mode (no UI exposure)

## Troubleshooting

**Queue not processing:**
- Check Supabase connection
- Verify queue has pending URLs
- Check GitHub Actions logs

**LLM extraction failing:**
- Check OpenRouter API key
- Verify free model availability
- Check rate limits

**Scout not finding URLs:**
- Verify Lemon8 page structure hasn't changed
- Increase `max_scrolls` parameter
- Check browser logs
