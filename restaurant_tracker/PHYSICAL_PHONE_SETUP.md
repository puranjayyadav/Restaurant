# Setting Up Physical Phone for Development

## ✅ What's Already Done

1. ✅ Flutter app updated to use `http://192.168.1.163:8000` for physical devices
2. ✅ Django server is running on `0.0.0.0:8000` (accessible from network)
3. ✅ Port 8000 is accessible locally

## 🔧 Required Steps

### Step 1: Allow Windows Firewall (Run as Administrator)

Open PowerShell **as Administrator** and run:

```powershell
netsh advfirewall firewall add rule name="Django Development Server" dir=in action=allow protocol=TCP localport=8000
```

Or manually:
1. Press `Win + R`, type `wf.msc`, press Enter
2. Click "Inbound Rules" → "New Rule"
3. Select "Port" → Next
4. Select "TCP" and enter port `8000` → Next
5. Select "Allow the connection" → Next
6. Check all profiles → Next
7. Name it "Django Development Server" → Finish

### Step 2: Verify Same WiFi Network

**Important:** Your phone and computer must be on the **same WiFi network**.

- Check phone WiFi: Settings → WiFi → Connected network name
- Check computer WiFi: Look at your network name in Windows
- They must match!

### Step 3: Test from Phone Browser

On your phone, open a browser and visit:
```
http://192.168.1.163:8000/api/discovery/featured-itineraries/?limit=8
```

You should see JSON data. If you get a connection error, check:
- Firewall rule is added
- Both devices on same WiFi
- Django server is running

### Step 4: Update IP if It Changes

If your computer's IP address changes (after restarting router, etc.):

1. Find new IP:
   ```powershell
   ipconfig | findstr /i "IPv4"
   ```

2. Update `api_service.dart`:
   ```dart
   return 'http://YOUR_NEW_IP:8000';
   ```

## 🧪 Testing

1. **Start Django server:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

2. **Run Flutter app on phone:**
   - Connect phone via USB
   - Run: `flutter run`
   - Or use wireless debugging

3. **Check Django terminal:**
   You should see request logs:
   ```
   ============================================================
   DEBUG: Incoming Request
     Method: GET
     Path: /api/discovery/featured-itineraries/
     Remote Address: 192.168.1.XXX  (your phone's IP)
   ============================================================
   ```

## 🔍 Troubleshooting

### Phone can't connect:
1. ✅ Check firewall rule is added
2. ✅ Verify same WiFi network
3. ✅ Test from phone browser first
4. ✅ Check Django is running on `0.0.0.0:8000` (not just `127.0.0.1:8000`)

### IP address changed:
- Update the IP in `api_service.dart` (line ~19)

### Still not working:
- Try temporarily disabling Windows Firewall to test
- Check if antivirus is blocking connections
- Verify phone can reach other devices on network

