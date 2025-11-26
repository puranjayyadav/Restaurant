# 🚂 Railway Deployment Guide - Step by Step

## Complete Guide to Deploy Your Django Backend on Railway

---

## ✅ Prerequisites

- [ ] Code pushed to GitHub
- [ ] GitHub account
- [ ] Railway account (free to create)

---

## 🚀 Part 1: Deploy to Railway (5 minutes)

### Step 1: Sign Up for Railway

1. Go to https://railway.app
2. Click **"Login"** or **"Start a New Project"**
3. Sign in with your **GitHub account**
4. Authorize Railway to access your repositories

### Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your backend repository (e.g., `food-explorer-backend`)
4. Railway will automatically detect it's a Django app!
5. Click **"Deploy Now"**

### Step 3: Wait for Initial Deployment

Railway will:
- ✅ Detect Python/Django
- ✅ Install dependencies from `requirements.txt`
- ✅ Build your app
- ✅ Deploy it!

**This takes 2-3 minutes. Watch the logs!**

---

## 🔧 Part 2: Add PostgreSQL Database

### Step 1: Add Database to Project

1. In your Railway project dashboard
2. Click **"New"** button (top right)
3. Select **"Database"**
4. Choose **"PostgreSQL"**
5. Click **"Add PostgreSQL"**

### Step 2: Connect Database to Backend

Railway automatically adds the `DATABASE_URL` environment variable!

**You don't need to do anything - it's automatic! 🎉**

---

## ⚙️ Part 3: Configure Environment Variables

### Step 1: Open Variables Tab

1. Click on your **web service** (not the database)
2. Go to **"Variables"** tab

### Step 2: Add Required Variables

Click **"+ New Variable"** and add these one by one:

#### Variable 1: DEBUG
```
DEBUG=False
```

#### Variable 2: SECRET_KEY
Generate a new secret key first:
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Copy the output and add:
```
SECRET_KEY=paste-your-generated-key-here
```

#### Variable 3: DJANGO_SETTINGS_MODULE
```
DJANGO_SETTINGS_MODULE=my_new_project.settings_prod
```

#### Variable 4: ALLOWED_HOSTS
Get your Railway app URL first (looks like `your-app-production.railway.app`), then:
```
ALLOWED_HOSTS=your-app-production.railway.app
```

### Step 3: Save and Redeploy

After adding variables:
1. Railway will **automatically redeploy** your app
2. Wait 1-2 minutes for deployment to complete

---

## 🌐 Part 4: Get Your Backend URL

### Step 1: Open Settings

1. Click on your **web service**
2. Go to **"Settings"** tab
3. Scroll to **"Domains"** section

### Step 2: Generate Domain

1. Click **"Generate Domain"**
2. Railway creates a public URL like:
   ```
   https://your-app-production.railway.app
   ```
3. **Copy this URL!** You'll need it for your Flutter app

### Step 3: Test Your Backend

Open your browser and visit:
```
https://your-app-production.railway.app/api/
```

You should see a response (even if it's an error page, it means the backend is running!)

---

## 🔄 Part 5: Run Database Migrations

### Option A: Automatic (Already Done!)

The `Procfile` I created runs migrations automatically on each deployment:
```
release: python manage.py migrate --noinput
```

### Option B: Manual (If Needed)

If you need to run migrations manually:

1. In Railway dashboard, click your **web service**
2. Go to **"Deployments"** tab
3. Click on the latest deployment
4. You'll see logs showing migrations running

Or use Railway CLI:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Run migrations
railway run python manage.py migrate
```

---

## 📱 Part 6: Update Your Flutter App

### Step 1: Get Your Railway URL

Your backend URL will be something like:
```
https://food-explorer-backend-production.railway.app
```

### Step 2: Update api_service.dart

Open `restaurant_tracker/lib/api_service.dart` and add at the top of the class:

```dart
class ApiService {
  // Railway Backend URL
  static const String BASE_URL = 'https://your-app-production.railway.app';
  
  final String googleApiKey = 'AIzaSyCqeTKWDSpdukY0rG3_0jipiGY1W5UU_28';
  
  // Update all API calls to use BASE_URL
  Future<Map<String, dynamic>> generateDayItinerary(...) async {
    final Uri url = Uri.parse('$BASE_URL/api/generate-day-itinerary/');
    // ... rest of code
  }
  
  // Do this for ALL API endpoint calls
}
```

### Step 3: Find and Replace All URLs

Search for:
- `http://10.0.2.2:8000/api/`
- `http://127.0.0.1:8000/api/`

Replace with:
- `$BASE_URL/api/`

### Step 4: Rebuild Flutter App

```powershell
cd restaurant_tracker
..\flutter\bin\flutter.bat clean
..\flutter\bin\flutter.bat pub get
..\flutter\bin\flutter.bat run
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Railway deployment shows "Success" status
- [ ] Can access `https://your-app.railway.app/api/` in browser
- [ ] Environment variables are set correctly
- [ ] PostgreSQL database is connected
- [ ] Migrations completed successfully
- [ ] Flutter app updated with new URL
- [ ] Flutter app can connect to backend
- [ ] Itinerary generation works
- [ ] Images load correctly

---

## 📊 Railway Dashboard Overview

### What Each Tab Does:

**Deployments:**
- See build and deployment logs
- Check deployment status
- View historical deployments

**Metrics:**
- CPU usage
- Memory usage
- Request count

**Variables:**
- Environment variables
- Database connection strings

**Settings:**
- Domain configuration
- Service settings
- Delete service

---

## 💰 Railway Pricing

### Free Tier:
- **$5 free credit per month**
- **500 execution hours**
- Perfect for testing and small projects

### After Free Tier:
- **$5/month** for 500 hours
- **Pay-as-you-go** after that

### Your App Should Cost:
- **~$5/month** for hobby/development use
- **~$10-20/month** if you get decent traffic

---

## 🔄 Future Updates

When you make code changes:

```bash
# In my_new_project folder
git add .
git commit -m "Your update message"
git push origin main
```

**Railway automatically redeploys!** 🎉

---

## 🆘 Troubleshooting

### Issue: "Application Failed"

**Check the logs:**
1. Railway Dashboard → Deployments → Click on deployment → View Logs

**Common causes:**
- Missing environment variable
- Wrong `SECRET_KEY`
- Database migration failed
- Wrong `ALLOWED_HOSTS`

### Issue: "DisallowedHost at /"

**Solution:**
Add your Railway domain to `ALLOWED_HOSTS`:
```
ALLOWED_HOSTS=your-app-production.railway.app
```

### Issue: "502 Bad Gateway"

**Solution:**
Your app is crashing. Check logs for error messages.

### Issue: "Database connection failed"

**Solution:**
Make sure PostgreSQL is added and `DATABASE_URL` variable exists.

### Issue: "CORS Error" in Flutter App

**Solution:**
CORS should be fine for mobile apps, but if you get errors, update `settings_prod.py`:
```python
CORS_ALLOW_ALL_ORIGINS = True  # Only for mobile apps
```

---

## 📞 Getting Help

- **Railway Docs:** https://docs.railway.app/
- **Railway Discord:** https://discord.gg/railway
- **Railway Status:** https://status.railway.app/

---

## 🎉 You're Done!

Your backend is now live on Railway! 🚀

**Your API endpoints:**
- Base URL: `https://your-app.railway.app`
- Create session: `https://your-app.railway.app/api/create_session/`
- Generate itinerary: `https://your-app.railway.app/api/generate-day-itinerary/`

**Next steps:**
1. Update Flutter app with new URL
2. Test all features
3. Deploy Flutter app to Play Store!

---

**Need help? Check the logs in Railway dashboard first - they're very detailed!**

