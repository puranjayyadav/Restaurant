# 🚀 Backend Deployment Instructions

## Your Django backend is ready to deploy!

## 📦 What I've Created

1. **`requirements.txt`** - All Python dependencies
2. **`Procfile`** - Tells Railway/Heroku how to run your app
3. **`runtime.txt`** - Specifies Python 3.11.9
4. **`railway.json`** - Railway configuration
5. **`render.yaml`** - Render.com configuration
6. **`settings_prod.py`** - Production-ready Django settings
7. **`.gitignore`** - Prevents committing sensitive files

---

## 🏆 Option 1: Deploy to Railway (RECOMMENDED)

### Step 1: Push to GitHub

```powershell
cd my_new_project
git init
git add .
git commit -m "Prepare backend for deployment"
git branch -M main
# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to https://railway.app and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Django and deploy!

### Step 3: Add Environment Variables

In Railway dashboard → Variables tab, add:

```
DEBUG=False
SECRET_KEY=your-new-secret-key-here-generate-one
DJANGO_SETTINGS_MODULE=my_new_project.settings_prod
ALLOWED_HOSTS=your-app.railway.app
```

**Generate a secret key:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 4: Add PostgreSQL Database

1. In Railway, click "New" → "Database" → "PostgreSQL"
2. Railway automatically adds `DATABASE_URL` environment variable
3. Your app will connect automatically!

### Step 5: Run Migrations

In Railway dashboard → Deployments → Click on your deployment → "View Logs"

Or use Railway CLI:
```bash
railway run python manage.py migrate
```

### Step 6: Update Flutter App

Your API will be at: `https://your-app.railway.app/api/`

Update `restaurant_tracker/lib/api_service.dart`:

```dart
// Change from:
final Uri url = Uri.parse('http://10.0.2.2:8000/api/...');

// To:
final Uri url = Uri.parse('https://your-app.railway.app/api/...');
```

**Done! Your backend is live! 🎉**

---

## 🔷 Option 2: Deploy to Render

### Step 1: Push to GitHub (same as above)

### Step 2: Deploy on Render

1. Go to https://render.com and sign up
2. Click "New+" → "Web Service"
3. Connect your GitHub repository
4. Render detects Django automatically!

### Step 3: Configure

- **Name:** food-explorer-backend
- **Region:** Choose closest to you
- **Branch:** main
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn my_new_project.wsgi:application`

### Step 4: Add Environment Variables

```
DEBUG=False
SECRET_KEY=your-generated-secret-key
DJANGO_SETTINGS_MODULE=my_new_project.settings_prod
PYTHON_VERSION=3.11.9
```

### Step 5: Add PostgreSQL

1. Click "New+" → "PostgreSQL"
2. Copy the Internal Database URL
3. Add to environment variables as `DATABASE_URL`

### Step 6: Deploy!

Click "Create Web Service"

**Your API:** `https://your-app.onrender.com/api/`

---

## ☁️ Option 3: Deploy to Google Cloud Run

### Prerequisites

Install Google Cloud SDK:
```powershell
# Download from https://cloud.google.com/sdk/docs/install
```

### Step 1: Create Dockerfile

I'll create this for you (see below).

### Step 2: Build and Deploy

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Build the container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/food-explorer-backend

# Deploy to Cloud Run
gcloud run deploy food-explorer-backend \
  --image gcr.io/YOUR_PROJECT_ID/food-explorer-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances YOUR_INSTANCE \
  --set-env-vars "DEBUG=False,SECRET_KEY=your-secret"
```

---

## 🔧 After Deployment: Update Flutter App

### Update API Base URL

**File:** `restaurant_tracker/lib/api_service.dart`

Find all instances of:
```dart
'http://10.0.2.2:8000/api/'
'http://127.0.0.1:8000/api/'
```

Replace with your deployed URL:
```dart
'https://your-app.railway.app/api/'
```

### Test Your API

Visit these URLs in your browser:
- `https://your-app.railway.app/api/` (should show API endpoints)
- `https://your-app.railway.app/admin/` (Django admin)

---

## ✅ Post-Deployment Checklist

After deploying, verify:

- [ ] API endpoints are accessible
- [ ] Database migrations ran successfully
- [ ] Environment variables are set correctly
- [ ] Static files are served properly
- [ ] CORS is configured for your mobile app
- [ ] Firebase integration works
- [ ] Google Maps API calls work
- [ ] Update API URL in Flutter app
- [ ] Test app on phone with production backend

---

## 🆘 Troubleshooting

### "Application Error" / 500 Error
**Check the logs in your hosting dashboard**

### "DisallowedHost" Error
**Add your domain to `ALLOWED_HOSTS` environment variable**

### Database Errors
**Make sure migrations ran:** `python manage.py migrate`

### CORS Errors in Flutter App
**Update `CORS_ALLOWED_ORIGINS` in settings_prod.py**

### Static Files Not Loading
**Run:** `python manage.py collectstatic --noinput`

---

## 💰 Cost Estimate

- **Railway:** $0 (500 hours free) → $5/month
- **Render:** $0 (free tier with cold starts) → $7/month
- **Google Cloud Run:** $0 (free tier 2M requests) → pay-as-you-go

**Recommended for your app:** Railway $5/month

---

## 📊 Monitoring

### Railway
- View logs: Dashboard → Deployments → View Logs
- View metrics: Dashboard → Metrics

### Render
- View logs: Dashboard → Logs
- View metrics: Dashboard → Metrics

---

## 🔄 Updating Your Backend

After making code changes:

```bash
git add .
git commit -m "Update backend"
git push
```

Railway/Render will automatically redeploy! 🚀

---

**Questions? Check the main hosting guide: `BACKEND_HOSTING_GUIDE.md`**

