# 🚀 Render Deployment Guide

## Prerequisites

1. **GitHub Repository**: Your code should be pushed to GitHub
2. **Render Account**: Sign up at [render.com](https://render.com) (free tier available)

## Step-by-Step Deployment

### Step 1: Prepare Your Repository

Ensure these files are in your `my_new_project` directory:
- ✅ `requirements.txt` - Python dependencies
- ✅ `Procfile` - Tells Render how to run your app
- ✅ `runtime.txt` - Python version (3.11.9)
- ✅ `build.sh` - Build script (optional but recommended)

### Step 2: Create Web Service on Render

1. Go to [render.com](https://render.com) and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account if not already connected
4. Select your repository
5. Configure the service:

   **Name**: `django-backend` (or your preferred name)
   
   **Root Directory**: `my_new_project`
   
   **Environment**: `Python 3`
   
   **Build Command**: 
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```
   
   **Start Command**: 
   ```bash
   gunicorn my_new_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
   ```

### Step 3: Configure Environment Variables

In Render dashboard → **Environment** tab, add these variables:

#### Required Variables:

```
DEBUG=False
SECRET_KEY=<generate-a-new-secret-key>
ALLOWED_HOSTS=your-app-name.onrender.com
```

**Generate SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Database (Choose One):

**Option A: Use Supabase PostgreSQL (Recommended - Free)**
```
DATABASE_URL=postgresql://user:password@host:port/dbname
```
Get this from your Supabase project → Settings → Database → Connection string

**Option B: Use Render PostgreSQL**
1. Create PostgreSQL database in Render (free for 90 days)
2. Render automatically adds `DATABASE_URL` environment variable

#### API Keys:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
OPENROUTER_API_KEYv3=your-openrouter-key
GOOGLE_MAPS_API_KEY=your-google-maps-key
```

#### CORS (if needed):

```
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://your-flutter-app.com,https://your-domain.com
```

### Step 4: Run Database Migrations

After first deployment:

1. Go to Render dashboard → Your service → **Shell**
2. Run:
   ```bash
   python manage.py migrate
   ```

Or add to build script (already included in `build.sh`)

### Step 5: Verify Deployment

1. Check deployment logs in Render dashboard
2. Visit your app URL: `https://your-app-name.onrender.com`
3. Test an API endpoint: `https://your-app-name.onrender.com/api/api/generate-itinerary/`

## Important Notes

### Free Tier Limitations:

- ⚠️ **Spins down after 15 minutes** of inactivity
- ⚠️ **Cold starts** take 30-60 seconds after spin-down
- ⚠️ **512 MB RAM** limit
- ⚠️ **PostgreSQL expires** after 90 days (then $7/month)

### Recommendations:

1. **Use Supabase PostgreSQL** instead of Render's database (free tier available)
2. **Upgrade to $7/month** if you need:
   - Always-on service (no spin-downs)
   - More RAM for heavy operations
   - Better performance

### Troubleshooting:

**Build fails:**
- Check `requirements.txt` for all dependencies
- Verify Python version in `runtime.txt` matches Render's Python 3.11.9

**App crashes:**
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure `ALLOWED_HOSTS` includes your Render URL

**Database connection fails:**
- Verify `DATABASE_URL` is correct
- Check database is accessible from Render's IP
- For Supabase: Ensure connection pooling is configured

**Static files not loading:**
- Verify `collectstatic` runs in build command
- Check `STATIC_ROOT` is set in settings.py
- Ensure WhiteNoise is configured (already done)

## Update Flutter App

After deployment, update your Flutter app's API base URL:

In `restaurant_tracker/lib/api_service.dart`:

```dart
static const String baseUrl = 'https://your-app-name.onrender.com';
```

## Monitoring

- View logs: Render dashboard → Your service → **Logs**
- Monitor metrics: Render dashboard → Your service → **Metrics**
- Set up alerts: Render dashboard → Your service → **Alerts**

## Next Steps

1. Set up custom domain (optional)
2. Configure auto-deploy from GitHub
3. Set up health checks
4. Monitor performance and upgrade if needed

