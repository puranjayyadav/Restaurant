# Fix Android Emulator Connection to Django Server

## Problem
Flutter app on Android emulator can't connect to Django server running on host machine.

## Solutions

### Solution 1: Check Windows Firewall (Most Common Issue)

1. **Open Windows Defender Firewall:**
   - Press `Win + R`, type `wf.msc`, press Enter

2. **Create Inbound Rule:**
   - Click "Inbound Rules" → "New Rule"
   - Select "Port" → Next
   - Select "TCP" and enter port `8000` → Next
   - Select "Allow the connection" → Next
   - Check all profiles (Domain, Private, Public) → Next
   - Name it "Django Development Server" → Finish

3. **Create Outbound Rule (if needed):**
   - Repeat above for "Outbound Rules"

### Solution 2: Use Your Local IP Address

Instead of `10.0.2.2`, try using your actual local IP address:

1. **Find your IP:**
   ```powershell
   ipconfig | findstr /i "IPv4"
   ```
   (You should see: `192.168.1.163`)

2. **Update Flutter app:**
   In `api_service.dart`, temporarily change:
   ```dart
   if (!kIsWeb && Platform.isAndroid) {
     return 'http://192.168.1.163:8000';  // Use your actual IP
   }
   ```

3. **Update Django to allow this IP:**
   Django is already configured with `ALLOWED_HOSTS = ['*']`, so this should work.

### Solution 3: Verify Emulator Network

1. **Check if emulator can reach internet:**
   - Open browser in emulator
   - Try visiting `http://google.com`

2. **Test connection from emulator:**
   - Open browser in emulator
   - Try: `http://10.0.2.2:8000/api/discovery/featured-itineraries/?limit=8`

### Solution 4: Use ADB Port Forwarding

Forward port from emulator to host:

```bash
adb reverse tcp:8000 tcp:8000
```

Then in Flutter, use `localhost:8000` instead of `10.0.2.2:8000`:

```dart
if (!kIsWeb && Platform.isAndroid) {
  return 'http://localhost:8000';  // After port forwarding
}
```

### Solution 5: Check Django Server Logs

With the new logging middleware, you should see requests in Django terminal:
- If you see the request logs → Connection is working, check Django response
- If you don't see any logs → Connection is blocked (likely firewall)

## Quick Test

Run this in PowerShell to test if port is accessible:
```powershell
Test-NetConnection -ComputerName localhost -Port 8000
```

If this fails, Django might not be running or firewall is blocking.

## Recommended Fix Order

1. ✅ Add Windows Firewall rule (Solution 1)
2. ✅ Restart Django server
3. ✅ Test from emulator browser: `http://10.0.2.2:8000`
4. ✅ If still fails, try ADB port forwarding (Solution 4)
5. ✅ If still fails, use local IP address (Solution 2)

