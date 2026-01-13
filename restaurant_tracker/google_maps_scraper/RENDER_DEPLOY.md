# Deploying Google Maps Scraper to Render

This guide explains how to deploy the Google Maps Scraper to [Render](https://render.com).

## 📋 Prerequisites

1. A Render account (free tier available)
2. Your code pushed to a GitHub repository
3. Supabase credentials (SUPABASE_URL and SUPABASE_KEY)

---

## 🚀 Deployment Options

### Option A: Cron Job (Recommended for scheduled scraping)

A **Cron Job** runs your scraper on a schedule (e.g., every 15 minutes) and shuts down between runs. This is cost-efficient.

#### Steps:

1. **Go to Render Dashboard** → [dashboard.render.com](https://dashboard.render.com)

2. **Click "New +" → "Cron Job"**

3. **Connect your GitHub repository**
   - Select the repository containing this code
   - Select the branch (usually `main`)

4. **Configure the Cron Job:**
   | Setting | Value |
   |---------|-------|
   | **Name** | `google-maps-scraper` |
   | **Region** | Choose closest to you |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r google_maps_scraper/requirements.txt` |
   | **Start Command** | `python google_maps_scraper/github_actions_runner.py` |
   | **Schedule** | `*/15 * * * *` (every 15 minutes) |

5. **Add Environment Variables:**
   - Click "Environment" section
   - Add:
     - `SUPABASE_URL` = your Supabase project URL
     - `SUPABASE_KEY` = your Supabase anon/service key

6. **Click "Create Cron Job"**

---

### Option B: Background Worker (Runs continuously)

A **Background Worker** runs continuously. Use this if you want the scraper to run in a loop.

> ⚠️ This uses more resources and costs more than a cron job.

#### Steps:

1. **Go to Render Dashboard** → "New +" → "Background Worker"

2. **Connect your GitHub repository**

3. **Configure the Worker:**
   | Setting | Value |
   |---------|-------|
   | **Name** | `google-maps-scraper-worker` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r google_maps_scraper/requirements.txt` |
   | **Start Command** | `python google_maps_scraper/github_actions_runner.py` |

4. **Add Environment Variables** (same as above)

5. **Click "Create Background Worker"**

---

### Option C: Blueprint Deployment (Infrastructure as Code)

Use the provided `render.yaml` for one-click deployment:

1. Update `render.yaml` with your GitHub repo URL
2. Push to GitHub
3. Go to Render → "Blueprints" → Connect repo
4. Render will auto-detect `render.yaml` and deploy

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | ✅ |
| `SUPABASE_KEY` | Your Supabase anon or service role key | ✅ |

### Cron Schedule Examples

| Schedule | Description |
|----------|-------------|
| `*/15 * * * *` | Every 15 minutes |
| `0 * * * *` | Every hour |
| `0 */2 * * *` | Every 2 hours |
| `0 0 * * *` | Once daily at midnight |
| `0 6,18 * * *` | Twice daily at 6 AM and 6 PM |

---

## 💡 Tips

### Modifying Scraper Behavior

Edit `github_actions_runner.py` to change:
- `VIBES_PER_RUN` - Number of vibe/location combos per run (default: 5)
- `REVIEWS_PER_RUN` - Number of venues to enrich with reviews (default: 15)

### Viewing Logs

1. Go to your service on Render
2. Click "Logs" tab
3. View real-time or historical logs

### Costs

| Service Type | Free Tier | Notes |
|--------------|-----------|-------|
| **Cron Job** | ❌ (Starter $7/mo) | Only runs when scheduled |
| **Background Worker** | ❌ (Starter $7/mo) | Runs 24/7 |

> Note: Render's free tier doesn't support cron jobs or background workers. The minimum is the Starter tier at ~$7/month.

---

## 🔄 Migrating from GitHub Actions

If you're currently using GitHub Actions:

1. Your Supabase state management will work the same way
2. The same `github_actions_runner.py` script works on both platforms
3. Just copy your environment variables from GitHub Secrets to Render

---

## 🐛 Troubleshooting

### Build fails
- Check if `requirements.txt` exists and has all dependencies
- Ensure Python version is compatible (3.9+)

### Scraper not saving data
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are set correctly
- Check Render logs for connection errors

### Rate limiting
- Google may rate limit requests
- Consider increasing delay between requests in `github_actions_runner.py`
