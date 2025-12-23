# 🚀 GitHub Actions Deployment - Quick Start

## What You Have

A fully automated scraping system that runs every 15 minutes:
- ✅ Scrapes Google Maps venues
- ✅ Enriches with reviews  
- ✅ Saves everything to Supabase
- ✅ Rotates through vibes and neighborhoods
- ✅ Zero maintenance required

## Files Created

```
.github/workflows/scraper.yml          # GitHub Actions workflow
google_maps_scraper/
  ├── github_actions_runner.py         # Main orchestrator
  ├── requirements.txt                 # Python dependencies
  ├── GITHUB_ACTIONS_SETUP.md          # Detailed setup guide
  └── scraper_counter.txt              # (will be created on first run)
```

## 5-Minute Setup

### 1. Push to GitHub

```bash
cd "C:\Users\PURANJAY\OneDrive\Documents\Res_2"

# Add and commit
git add .
git commit -m "Add automated scraper with GitHub Actions"

# Push (replace with your repo URL)
git push origin main
```

### 2. Add Secrets

Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions`

Add two secrets:
- **SUPABASE_URL**: `https://diytyziczzosylmyrfxo.supabase.co`
- **SUPABASE_KEY**: (your Supabase anon key)

### 3. Enable Actions

1. Go to your repo → **Actions** tab
2. Click **I understand my workflows, go ahead and enable them**

### 4. Test Run

1. Go to **Actions** → **Google Maps Scraper**
2. Click **Run workflow** → **Run workflow**
3. Watch it run!

## What Happens Every 15 Minutes

```
16:00 → Scrape SoHo work_friendly cafes → Enrich 5 venues with reviews
16:15 → Scrape SoHo aesthetic cafes → Enrich 5 venues with reviews
16:30 → Scrape SoHo speakeasy bars → Enrich 5 venues with reviews
...and so on
```

## Expected Output

### Per Day
- **Venues**: ~9,600-19,200 new venues
- **Reviews**: ~2,400 reviews

### Per Week
- **Venues**: ~67,000-134,000 venues
- **Reviews**: ~16,800 reviews

---

**Ready to deploy!** 🚀 See GITHUB_ACTIONS_SETUP.md for full details.
