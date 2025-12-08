@echo off
echo Starting Django server for Android emulator access...
echo.
echo The server will be accessible at:
echo   - Android Emulator: http://10.0.2.2:8000
echo   - Local browser: http://localhost:8000
echo.
python manage.py runserver 0.0.0.0:8000

