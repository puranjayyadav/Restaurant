# GitHub Actions Setup Guide

## Overview

This setup runs the Google Maps scraper automatically every 15 minutes using GitHub Actions:
- **Venue Scraping**: Rotates through vibes and neighborhoods
- **Review Enrichment**: Adds reviews to 5 venues per run
- **All data saved to Supabase**

## Setup Steps

### 1. Push Code to GitHub

```bash
cd c:\Users\PURANJAY\OneDrive\Documents\Res_2

# Initialize git (if not already done)
git init

# Add files
git add .github/workflows/scraper.yml
git add google_maps_scraper/

# Commit
git commit -m "Add automated scraper workflow"

# Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Add GitHub Secrets

Go to your GitHub repository:
1. Click **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these two secrets:

**Secret 1:**
- Name: `SUPABASE_URL`
- Value: `https://diytyziczzosylmyrfxo.supabase.co`

**Secret 2:**
- Name: `SUPABASE_KEY`
- Value: Your Supabase anon key (from Supabase dashboard → Settings → API)

### 3. Enable GitHub Actions

1. Go to your repository on GitHub
2. Click **Actions** tab
3. If prompted, click **I understand my workflows, go ahead and enable them**

### 4. Test Manual Run

1. Go to **Actions** tab
2. Click **Google Maps Scraper** workflow
3. Click **Run workflow** → **Run workflow**
4. Watch it run!

## How It Works

### Schedule
- Runs every 15 minutes: `:00`, `:15`, `:30`, `:45`
- Each run takes ~5-10 minutes
- 96 runs per day = ~192 vibes scraped + ~480 reviews added

### Rotation Strategy

The scraper rotates through:

**Vibes** (8 total):
1. work_friendly
2. aesthetic
3. speakeasy
4. coffee_run
5. brunch_buzzy
6. rooftop
7. natural_wine
8. dinner_date

**Neighborhoods** (5 total):
1. SoHo
2. Williamsburg
3. East Village
4. West Village
5. Tribeca

**Pattern**:
```
Run 1:  SoHo + work_friendly
Run 2:  SoHo + aesthetic
Run 3:  SoHo + speakeasy
...
Run 8:  SoHo + dinner_date
Run 9:  Williamsburg + work_friendly
Run 10: Williamsburg + aesthetic
...
```

After 40 runs (10 hours), it cycles back to the start.

### Per Run

Each 15-minute run:
1. **Scrapes**: 1 vibe in 1 neighborhood (~100-200 venues)
2. **Enriches**: 5 venues with reviews (~25 reviews total)
3. **Saves**: Everything to Supabase
4. **Updates**: Counter file (tracks rotation)

### Daily Output

- **Venues**: ~9,600-19,200 new venues per day
- **Reviews**: ~2,400 reviews per day
- **Coverage**: All 8 vibes × 5 neighborhoods = 40 combinations every 10 hours

## Monitoring

### Check Workflow Status

1. Go to **Actions** tab on GitHub
2. See recent runs and their status
3. Click any run to see detailed logs

### Check Supabase

```sql
-- Count total venues
SELECT COUNT(*) FROM venues;

-- Count venues by vibe
SELECT vibe_slug, COUNT(*) 
FROM venue_vibes 
GROUP BY vibe_slug;

-- Count reviews
SELECT COUNT(*) FROM reviews;

-- Recent activity
SELECT created_at, COUNT(*) 
FROM venues 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY created_at
ORDER BY created_at DESC;
```

### View Logs

Each run prints:
- Which vibe/neighborhood is being scraped
- Number of venues found
- Number of reviews added
- Success/failure status

## Customization

### Change Schedule

Edit `.github/workflows/scraper.yml`:

```yaml
# Every 30 minutes instead of 15
- cron: '*/30 * * * *'

# Every hour
- cron: '0 * * * *'

# Only during business hours (9am-5pm EST)
- cron: '0 9-17 * * *'
```

### Change Vibes/Neighborhoods

Edit `google_maps_scraper/github_actions_runner.py`:

```python
VIBE_ROTATION = [
    ("your_vibe", "your search query"),
    # Add more...
]

NEIGHBORHOODS = [
    "Your Neighborhood, City, State",
    # Add more...
]
```

### Change Venues/Reviews Per Run

Edit `google_maps_scraper/github_actions_runner.py`:

```python
REVIEWS_PER_RUN = 10  # Enrich 10 venues instead of 5
```

## Troubleshooting

### Workflow Not Running

- Check if Actions are enabled in repository settings
- Verify cron syntax is correct
- Check if you have GitHub Actions minutes remaining (free tier = 2000 min/month)

### Scraper Failing

- Check GitHub Actions logs for errors
- Verify Supabase secrets are set correctly
- Check if Supabase is accessible from GitHub's IP

### No Data in Supabase

- Verify secrets are correct
- Check workflow logs for errors
- Test locally first: `python github_actions_runner.py`

### Rate Limiting

If you get rate limited:
- Reduce frequency (every 30 min instead of 15)
- Reduce grid size in `run_grid_search(grid_dimension=1)`
- Add longer delays in `advanced_grid_scraper.py`

## Cost Estimate

### GitHub Actions
- Free tier: 2000 minutes/month
- Each run: ~10 minutes
- 96 runs/day × 10 min = 960 min/day
- **Monthly**: ~28,800 minutes ❌ **Exceeds free tier!**

**Solution**: Run every 30 minutes instead:
- 48 runs/day × 10 min = 480 min/day
- **Monthly**: ~14,400 minutes ✅ **Within free tier!**

### Supabase
- Free tier: 500 MB database, 2 GB bandwidth
- Estimated usage: ~100 MB/month ✅ **Within free tier!**

## Recommended Schedule

For free tier, use:

```yaml
# Every 30 minutes (stays within free tier)
- cron: '*/30 * * * *'
```

This gives you:
- 48 runs/day
- ~4,800-9,600 venues/day
- ~1,200 reviews/day
- Still excellent coverage!

---

**Status**: Ready to deploy  
**Estimated setup time**: 10 minutes  
**Maintenance**: Zero (fully automated)
