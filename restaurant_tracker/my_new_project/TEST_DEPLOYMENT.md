# 🧪 Testing Your Railway Deployment

## Step 1: Check Deployment Status

### In Railway Dashboard:

1. Go to https://railway.app
2. Open your project
3. Click on your web service
4. Look at the **Deployments** tab
5. Check the latest deployment status:
   - ✅ **Green "Success"** = Deployed!
   - 🔴 **Red "Failed"** = Check logs for errors
   - 🟡 **Yellow "Building"** = Wait for it to finish

---

## Step 2: Get Your Backend URL

### Method A: From Railway Dashboard

1. Click your web service
2. Go to **"Settings"** tab
3. Scroll to **"Domains"** section
4. If no domain exists:
   - Click **"Generate Domain"**
   - Copy the generated URL (e.g., `https://your-app-production.railway.app`)

### Method B: From Deployment

1. Click on the successful deployment
2. Look for the URL in the deployment details
3. Copy it

---

## Step 3: Test Your API Endpoints

### Test 1: Basic Health Check

Open your browser or use curl:

```bash
# Replace with YOUR Railway URL
https://your-app-production.railway.app/
```

**Expected Result:**
- Django default page, OR
- 404 page (this is OK - means Django is running!)
- **NOT** a connection error

### Test 2: Admin Interface

```bash
https://your-app-production.railway.app/admin/
```

**Expected Result:**
- Django admin login page
- If you see this, Django is definitely working!

### Test 3: API Endpoint

```bash
https://your-app-production.railway.app/api/
```

**Expected Result:**
- JSON response with API info, OR
- 404 (means Django is running but endpoint needs configuration)

---

## Step 4: Test from Command Line

### Using curl (PowerShell):

```powershell
# Test basic connection
curl https://your-app-production.railway.app/

# Test API endpoint
curl https://your-app-production.railway.app/api/

# Test with verbose output
curl -v https://your-app-production.railway.app/admin/
```

### Using PowerShell Invoke-WebRequest:

```powershell
Invoke-WebRequest -Uri "https://your-app-production.railway.app/" -Method GET
```

---

## Step 5: Test Specific Endpoints

### Test Create Session (if you have this endpoint):

```powershell
$url = "https://your-app-production.railway.app/api/create_session/"
$body = @{
    user_id = "test123"
    latitude = 40.7128
    longitude = -74.0060
} | ConvertTo-Json

Invoke-WebRequest -Uri $url -Method POST -Body $body -ContentType "application/json"
```

### Test Generate Itinerary:

```powershell
$url = "https://your-app-production.railway.app/api/generate-day-itinerary/"
$body = @{
    user_id = "test123"
    start_latitude = 40.7128
    start_longitude = -74.0060
    selected_categories = @("restaurant", "cafe")
    places_data = @()
} | ConvertTo-Json

Invoke-WebRequest -Uri $url -Method POST -Body $body -ContentType "application/json"
```

---

## Step 6: Check Deployment Logs

### If Something Doesn't Work:

1. Railway Dashboard → Your service
2. Click **Deployments** tab
3. Click on the latest deployment
4. View the **logs** to see what's happening

**Look for:**
- ✅ `[INFO] Listening at: http://0.0.0.0:8080`
- ✅ `[INFO] Booting worker with pid: X`
- ❌ Any ERROR or Exception messages

---

## Step 7: Common Issues & Solutions

### Issue: "Connection refused" or "Cannot reach site"

**Solution:**
1. Check Railway deployment status (must be "Success")
2. Wait 30 seconds after deployment
3. Make sure you generated a domain in Railway Settings
4. Check if service is running in Railway dashboard

### Issue: "DisallowedHost at /"

**Solution:**
Add environment variable in Railway:
```
ALLOWED_HOSTS=.railway.app
```

### Issue: "500 Internal Server Error"

**Solution:**
1. Check Railway logs for the actual error
2. Most common: Missing environment variables
3. Add these in Railway → Variables:
   - `DEBUG=False`
   - `SECRET_KEY=your-generated-key`
   - `ALLOWED_HOSTS=.railway.app`

### Issue: "CSRF verification failed"

**Solution:**
This is normal for POST requests without CSRF tokens. Your Flutter app will handle this correctly.

---

## Step 8: Test Database Connection

### Check if PostgreSQL is connected:

1. Railway Dashboard → Click PostgreSQL service
2. Copy the `DATABASE_URL`
3. In your web service → Variables tab
4. Verify `DATABASE_URL` exists (Railway adds this automatically)

### Run migrations (if needed):

Railway CLI method:
```bash
railway run python manage.py migrate
```

Or add to your Procfile (we removed this earlier):
```
release: python manage.py migrate --noinput
```

---

## ✅ Deployment Success Checklist

- [ ] Railway deployment shows "Success" status
- [ ] Domain generated and accessible
- [ ] Can access `https://your-app.railway.app/admin/`
- [ ] No "DisallowedHost" errors
- [ ] Logs show "Booting worker" without errors
- [ ] PostgreSQL database connected (if using)
- [ ] Environment variables set (DEBUG, SECRET_KEY, ALLOWED_HOSTS)
- [ ] Can make POST requests to API endpoints

---

## 🎯 Quick Test Script

Save this as `test_backend.ps1`:

```powershell
# Replace with your Railway URL
$BASE_URL = "https://your-app-production.railway.app"

Write-Host "Testing Railway Deployment..." -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Testing root endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BASE_URL/" -Method GET -ErrorAction Stop
    Write-Host "   ✓ Root endpoint accessible (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Root endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "2. Testing admin endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BASE_URL/admin/" -Method GET -ErrorAction Stop
    Write-Host "   ✓ Admin endpoint accessible (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Admin endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "3. Testing API endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BASE_URL/api/" -Method GET -ErrorAction Stop
    Write-Host "   ✓ API endpoint accessible (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   ✗ API endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Testing complete!" -ForegroundColor Cyan
```

Run it:
```powershell
.\test_backend.ps1
```

---

## 📱 Next Step: Update Flutter App

Once your backend is working, update your Flutter app:

**File:** `restaurant_tracker/lib/api_service.dart`

```dart
class ApiService {
  // Change this to your Railway URL
  static const String BASE_URL = 'https://your-app-production.railway.app';
  
  // Use BASE_URL in all API calls
  Future<Map<String, dynamic>> generateDayItinerary(...) async {
    final Uri url = Uri.parse('$BASE_URL/api/generate-day-itinerary/');
    // ...
  }
}
```

---

**Your backend should be live now! Check the Railway dashboard and test the URLs!** 🚀

