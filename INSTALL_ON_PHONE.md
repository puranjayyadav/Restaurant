# 📱 How to Install the App on Your Phone

Since your app is now configured to use the Render backend (`https://restaurant-unyn.onrender.com`), you can install it directly on your phone without needing a local server running.

## 🚀 Quick Start

### Prerequisites
1. ✅ Flutter installed on your computer
2. ✅ Phone connected via USB (or wireless debugging enabled)
3. ✅ Developer mode enabled on your phone

---

## 📱 For Android Phones

### Step 1: Enable Developer Options
1. Go to **Settings** → **About Phone**
2. Tap **Build Number** 7 times
3. You'll see "You are now a developer!"

### Step 2: Enable USB Debugging
1. Go to **Settings** → **Developer Options**
2. Enable **USB Debugging**
3. Enable **Install via USB** (if available)

### Step 3: Connect Your Phone
1. Connect phone to computer via USB cable
2. On your phone, when prompted, tap **Allow USB Debugging**
3. Check "Always allow from this computer" → **OK**

### Step 4: Verify Connection
Open PowerShell/Terminal and run:
```bash
flutter devices
```

You should see your phone listed, like:
```
sdk gphone64 arm64 (mobile) • emulator-5554 • android-arm64 • Android 13
```

### Step 5: Install the App
```bash
flutter run
```

This will:
- Build the app
- Install it on your phone
- Launch it automatically

**OR** build an APK file:
```bash
flutter build apk --release
```

Then install the APK from:
```
build/app/outputs/flutter-apk/app-release.apk
```

---

## 🍎 For iPhone (iOS)

### Step 1: Enable Developer Mode
1. Go to **Settings** → **Privacy & Security**
2. Scroll down to **Developer Mode**
3. Enable **Developer Mode**
4. Restart your iPhone

### Step 2: Trust Your Computer
1. Connect iPhone via USB
2. On iPhone, tap **Trust This Computer**
3. Enter your passcode

### Step 3: Verify Connection
```bash
flutter devices
```

You should see your iPhone listed.

### Step 4: Install the App
```bash
flutter run
```

**Note:** For iOS, you may need:
- Xcode installed on Mac
- Apple Developer account (free account works for testing)
- Sign the app in Xcode

---

## 🔧 Alternative: Build APK/IPA and Install Manually

### Android APK (Easiest Method)
```bash
# Build release APK
flutter build apk --release

# The APK will be at:
# build/app/outputs/flutter-apk/app-release.apk
```

Then:
1. Transfer APK to your phone (via USB, email, or cloud storage)
2. On phone: **Settings** → **Security** → Enable **Install from Unknown Sources**
3. Open the APK file and install

### iOS IPA (Requires Mac + Xcode)
```bash
flutter build ios --release
```

Then use Xcode to archive and export the IPA.

---

## 🧪 Testing the Connection

Once installed, the app should automatically connect to:
```
https://restaurant-unyn.onrender.com
```

### To Verify:
1. Open the app on your phone
2. Try generating an itinerary
3. Check the debug logs (if running via `flutter run`) - you should see:
   ```
   DEBUG: Using production baseUrl: https://restaurant-unyn.onrender.com
   ```

---

## 🐛 Troubleshooting

### Phone Not Detected
**Android:**
- Check USB cable (try different cable)
- Enable USB Debugging again
- Try different USB port
- Install/update USB drivers

**iOS:**
- Make sure you trusted the computer
- Check USB cable
- Restart both devices

### App Won't Install
**Android:**
- Enable "Install via USB" in Developer Options
- Check if phone has enough storage
- Uninstall old version first: `flutter uninstall`

**iOS:**
- Need to sign the app in Xcode
- Check Apple Developer account
- May need to trust the developer certificate on iPhone

### App Crashes on Launch
- Check if Render backend is running: Visit `https://restaurant-unyn.onrender.com/api/` in browser
- Check app logs: `flutter logs`
- Verify API connection in debug console

### Network Issues
- Make sure phone has internet connection
- Check if Render backend is accessible from phone's browser
- Verify CORS settings on backend (should allow all origins for now)

---

## 📝 Quick Commands Reference

```bash
# Check connected devices
flutter devices

# Run on connected device
flutter run

# Build Android APK
flutter build apk --release

# Build iOS (Mac only)
flutter build ios --release

# View logs
flutter logs

# Uninstall from device
flutter uninstall
```

---

## ✅ Success Checklist

- [ ] Phone connected and detected (`flutter devices` shows it)
- [ ] App installed successfully
- [ ] App launches without crashing
- [ ] Can generate an itinerary (tests backend connection)
- [ ] Backend responds (check Render dashboard)

---

## 🎉 You're Done!

Your app is now installed and connected to the Render backend. You can use it anywhere with internet access - no local server needed!

