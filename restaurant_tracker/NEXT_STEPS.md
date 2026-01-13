# Next Steps After Configuring Environment Variables

## ✅ Step 1: Set Up Database Schema (REQUIRED)

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **SQL Editor** (left sidebar)
4. Click **New Query**
5. Copy the entire contents of `supabase_schema.sql`
6. Paste it into the SQL Editor
7. Click **Run** (or press Ctrl+Enter)

This creates:
- `crawl_queue` table (manages discovered URLs)
- `lemon8_articles` table (stores scraped content and extracted data)

## ✅ Step 2: Test Connection

Run the test script to verify everything is working:

```bash
python test_supabase_connection.py
```

Expected output:
```
✓ Supabase client created
✓ Database connection successful!
Queue Statistics:
  Pending: 0
  Processing: 0
  Completed: 0
  Failed: 0
```

## ✅ Step 3: Run Scout (Discover URLs)

Discover article URLs and add them to the queue:

```bash
python scout_lemon8.py "https://www.lemon8-app.com/experience/new-york-eat?region=us"
```

This will:
- Visit the seed URL
- Auto-scroll to load content
- Extract article links
- Add them to `crawl_queue` table

## ✅ Step 4: Run Miner (Process Queue)

Process URLs from the queue:

```bash
python miner_lemon8.py 10
```

This will:
- Fetch 10 pending URLs from queue
- Scrape HTML content
- Extract itinerary data with LLM
- Save to `lemon8_articles` table

## ✅ Step 5: Verify in Supabase Dashboard

1. Go to **Table Editor** in Supabase
2. Check `crawl_queue` table - see discovered URLs
3. Check `lemon8_articles` table - see scraped content and extracted data

## 🔄 Step 6: Set Up GitHub Actions (Optional - for automation)

1. Push your code to GitHub
2. Go to repository → **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets (same values as in `.env`):
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `OPENROUTER_API_KEY`
4. The workflow will automatically run:
   - Scout every 6 hours
   - Miner every 2 hours

## Troubleshooting

**"Could not connect to Supabase"**
- Make sure you created `.env` file (not just `env.example`)
- Verify credentials in Supabase Dashboard → Settings → API

**"Tables don't exist"**
- Run `supabase_schema.sql` in Supabase SQL Editor

**"No pending URLs"**
- Run Scout first to discover URLs

**"Brave browser not found"**
- On Windows: Install Brave or update path in scripts
- Scripts will use system Chrome if Brave not found
