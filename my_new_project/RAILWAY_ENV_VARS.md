# 🔧 Railway Environment Variables

## Required Variables to Add in Railway Dashboard

Go to: Railway Dashboard → Your Service → **Variables** Tab

Click "Add Variable" for each of these:

---

### 1. PYTHONPATH
```
PYTHONPATH=/app
```
**Purpose:** Tells Python where to find your Django modules

---

### 2. DEBUG
```
DEBUG=False
```
**Purpose:** Disables debug mode in production

---

### 3. SECRET_KEY
```
SECRET_KEY=<paste-generated-key-here>
```

**Generate a key first:**
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Purpose:** Django security key (NEVER share this!)

---

### 4. ALLOWED_HOSTS
```
ALLOWED_HOSTS=.railway.app
```
**Purpose:** Allows Railway domains to access your Django app

---

### 5. DJANGO_SETTINGS_MODULE (Optional but recommended)
```
DJANGO_SETTINGS_MODULE=my_new_project.settings
```
**Purpose:** Explicitly tells Django which settings file to use

---

## How to Add Variables:

1. Go to https://railway.app
2. Open your project
3. Click your web service
4. Click **"Variables"** tab (left sidebar)
5. Click **"New Variable"**
6. Enter the name and value
7. Click **"Add"**
8. Railway will automatically redeploy

---

## After Adding Variables:

Railway will trigger a new deployment. Wait for it to complete, then test your app!

---

## Verify Variables Are Set:

In Railway Dashboard → Variables tab, you should see:
- ✅ PYTHONPATH=/app
- ✅ DEBUG=False  
- ✅ SECRET_KEY=(long random string)
- ✅ ALLOWED_HOSTS=.railway.app
- ✅ DATABASE_URL=(auto-added by Railway if you have PostgreSQL)

---

**After adding these, your deployment should work!** 🚀

