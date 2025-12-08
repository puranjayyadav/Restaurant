# GitHub Actions Setup Guide

## Step 1: Add GitHub Secrets

1. Go to your repository: https://github.com/puranjayyadav/Restaurant
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret**
5. Add these three secrets (use the same values from your `.env` file):

### Secret 1: SUPABASE_URL
- **Name:** `SUPABASE_URL`
- **Value:** `https://diytyziczzosylmyrfxo.supabase.co`

### Secret 2: SUPABASE_KEY
- **Name:** `SUPABASE_KEY`
- **Value:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpeXR5emljenpvc3lsbXlyZnhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ4NjYzOTMsImV4cCI6MjA4MDQ0MjM5M30.2Wet_5E82ippon8oDCvCV8X1g0POrO6uwUq9B5jgSr4`

### Secret 3: OPENROUTER_API_KEY
- **Name:** `OPENROUTER_API_KEY`
- **Value:** `sk-or-v1-your-actual-key-here` (get from https://openrouter.ai/keys)

## Step 2: Verify Workflow File

The workflow file is already in place at:
`.github/workflows/lemon8_crawler.yml`

It will automatically:
- **Scout**: Run every 6 hours (discovers new URLs)
- **Miner**: Run every 2 hours (processes queue)

## Step 3: Test the Workflow

1. Go to **Actions** tab in your GitHub repository
2. You should see "Lemon8 Snowball Crawler" workflow
3. Click **Run workflow** → **Run workflow** (manual trigger)
4. This will test both Scout and Miner jobs

## Step 4: Monitor Progress

- **Actions tab**: See workflow runs and logs
- **Supabase Dashboard**: See queue and articles tables
- Workflows run automatically on schedule

## Troubleshooting

**Workflow fails:**
- Check Actions tab for error logs
- Verify all 3 secrets are set correctly
- Check Supabase project is active

**No URLs discovered:**
- Scout might need more seed URLs
- Check Lemon8 page structure hasn't changed

**Queue not processing:**
- Verify Miner workflow is running
- Check Supabase connection in logs
