# Quick Setup Guide

## 1. Supabase Setup (5 minutes)

1. Go to https://supabase.com and create a free account
2. Create a new project
3. Go to **SQL Editor** and run the contents of `supabase_schema.sql`
4. Go to **Settings > API** and copy:
   - Project URL → `SUPABASE_URL`
   - anon/public key → `SUPABASE_KEY`

## 2. Local Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Copy `env.example` to `.env` and fill in your credentials:

```bash
cp env.example .env
```

Edit `.env`:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
OPENROUTER_API_KEY=sk-or-v1-...
```

### Test Locally

**Run Scout:**
```bash
python scout_lemon8.py "https://www.lemon8-app.com/experience/new-york-eat?region=us"
```

**Run Miner:**
```bash
python miner_lemon8.py 5  # Process 5 URLs
```

## 3. GitHub Actions Setup (Free Automation)

1. Push your code to GitHub
2. Go to your repository → **Settings → Secrets and variables → Actions**
3. Add these secrets:
   - `SUPABASE_URL` (from Supabase Settings > API)
   - `SUPABASE_KEY` (from Supabase Settings > API)
   - `OPENROUTER_API_KEY` (your OpenRouter key)
4. The workflow will automatically:
   - **Scout**: Run every 6 hours (discovers new URLs)
   - **Miner**: Run every 2 hours (processes queue)

## 4. Verify It's Working

Check your Supabase dashboard:
- **Table Editor → `crawl_queue`**: See discovered URLs
- **Table Editor → `lemon8_articles`**: See scraped content and extracted data

## Troubleshooting

**"Could not connect to Supabase"**
- Check your `.env` file has correct credentials
- Verify Supabase project is active

**"Brave browser not found"**
- On Windows: Install Brave or update path in scripts
- On GitHub Actions: This is normal, it uses system Chrome

**"No pending URLs"**
- Run Scout first to discover URLs
- Check `crawl_queue` table in Supabase

**GitHub Actions failing**
- Check Actions tab for error logs
- Verify all secrets are set correctly
- Check if Supabase project is active
