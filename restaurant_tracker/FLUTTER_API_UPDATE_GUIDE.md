# 📱 Flutter App API URL Update Guide

## After Deploying Your Backend

Once your Django backend is live, you need to update the API URLs in your Flutter app.

---

## 🔍 Files to Update

### File: `restaurant_tracker/lib/api_service.dart`

**Current URLs (localhost):**
```dart
'http://10.0.2.2:8000/api/...'  // For Android emulator
'http://127.0.0.1:8000/api/...'  // For local testing
```

**Change to your production URL:**
```dart
'https://your-app.railway.app/api/...'
```

---

## 📝 Step-by-Step Update

### Step 1: Find Your Production URL

After deploying to Railway/Render, you'll get a URL like:
- **Railway:** `https://your-app-production.railway.app`
- **Render:** `https://your-app.onrender.com`
- **Google Cloud:** `https://your-app-xxxxx.run.app`

### Step 2: Update api_service.dart

Open `restaurant_tracker/lib/api_service.dart` and update these locations:

#### Location 1: generateDayItinerary method (around line 760)
```dart
// OLD
final Uri url = Uri.parse('http://10.0.2.2:8000/api/generate-day-itinerary/');

// NEW
final Uri url = Uri.parse('https://your-app.railway.app/api/generate-day-itinerary/');
```

#### Location 2: Other API endpoints
Search for all instances of `10.0.2.2:8000` or `127.0.0.1:8000` and replace with your production URL.

### Step 3: Use a Constant (Best Practice)

**Add at the top of `api_service.dart`:**
```dart
class ApiService {
  // API Base URL - change this when deploying
  static const String BASE_URL = 'https://your-app.railway.app';
  
  final String googleApiKey = 'AIzaSyCqeTKWDSpdukY0rG3_0jipiGY1W5UU_28';
  
  // Then use it in your methods:
  Future<Map<String, dynamic>> generateDayItinerary(...) async {
    final Uri url = Uri.parse('$BASE_URL/api/generate-day-itinerary/');
    // ... rest of code
  }
}
```

**Benefits:**
- ✅ Only one place to update
- ✅ Easy to switch between dev/prod
- ✅ Less error-prone

---

## 🔄 Environment-Based URLs (Advanced)

Create separate configurations for development and production:

**Create:** `restaurant_tracker/lib/config.dart`
```dart
class Config {
  static const bool IS_PRODUCTION = true; // Change to false for local testing
  
  static String get apiBaseUrl {
    if (IS_PRODUCTION) {
      return 'https://your-app.railway.app';
    } else {
      return 'http://10.0.2.2:8000'; // For emulator
      // return 'http://127.0.0.1:8000'; // For web
    }
  }
}
```

**Use in `api_service.dart`:**
```dart
import 'config.dart';

class ApiService {
  final String baseUrl = Config.apiBaseUrl;
  
  Future<Map<String, dynamic>> generateDayItinerary(...) async {
    final Uri url = Uri.parse('$baseUrl/api/generate-day-itinerary/');
    // ...
  }
}
```

---

## ✅ Testing After Update

### 1. Test API Connection

Add a test endpoint call in your app:
```dart
void testBackendConnection() async {
  try {
    final response = await http.get(
      Uri.parse('$BASE_URL/api/test/'),
    );
    print('Backend connected: ${response.statusCode}');
  } catch (e) {
    print('Backend connection failed: $e');
  }
}
```

### 2. Check CORS

If you get CORS errors, update your Django backend:

**File:** `my_new_project/my_new_project/settings_prod.py`
```python
CORS_ALLOWED_ORIGINS = [
    'https://your-flutter-app-domain.com',
    # For mobile apps, CORS usually isn't an issue
]
```

### 3. Test All Features

- [ ] Category selection works
- [ ] Location detection works
- [ ] Itinerary generation works
- [ ] Images load
- [ ] Regenerate itinerary works

---

## 🚨 Common Issues

### Issue: "Connection refused"
**Solution:** Check your backend URL is correct and backend is running

### Issue: "Network error" / "Failed to connect"
**Solution:** 
1. Check your internet connection
2. Verify the backend URL is accessible (visit it in a browser)
3. Check if Railway/Render service is sleeping (free tier)

### Issue: "CORS error"
**Solution:** Add your app's domain to `CORS_ALLOWED_ORIGINS` in Django

### Issue: "404 Not Found"
**Solution:** Check the API endpoint path is correct (include `/api/` prefix)

### Issue: "500 Internal Server Error"
**Solution:** Check backend logs in Railway/Render dashboard

---

## 📋 Quick Checklist

Before releasing your app:
- [ ] Backend deployed and accessible
- [ ] All API URLs updated in Flutter app
- [ ] `BASE_URL` constant defined
- [ ] Tested itinerary generation
- [ ] Tested image loading
- [ ] Tested regenerate feature
- [ ] Verified backend logs show requests
- [ ] CORS configured if needed
- [ ] SSL/HTTPS working (should be automatic)

---

## 💡 Pro Tips

1. **Use a constant for the base URL** - easier to manage
2. **Add logging** - log API responses during development
3. **Handle errors gracefully** - show user-friendly messages
4. **Test on real device** - emulator might behave differently
5. **Monitor backend logs** - catch issues early

---

## 🆘 Need Help?

1. Check Railway/Render logs for backend errors
2. Use Flutter DevTools to inspect network requests
3. Test API endpoints directly in Postman/browser
4. Verify environment variables are set correctly

---

**After updating, rebuild and test your Flutter app!**

```powershell
cd restaurant_tracker
..\flutter\bin\flutter.bat clean
..\flutter\bin\flutter.bat pub get
..\flutter\bin\flutter.bat run
```

