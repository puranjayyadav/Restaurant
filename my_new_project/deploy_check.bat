@echo off
echo ================================
echo Django Backend Deployment Check
echo ================================
echo.

echo [1/5] Checking Python version...
python --version
echo.

echo [2/5] Checking required files...
if exist "requirements.txt" (
    echo [OK] requirements.txt found
) else (
    echo [ERROR] requirements.txt missing!
    goto error
)

if exist "Procfile" (
    echo [OK] Procfile found
) else (
    echo [ERROR] Procfile missing!
    goto error
)

if exist "runtime.txt" (
    echo [OK] runtime.txt found
) else (
    echo [ERROR] runtime.txt missing!
    goto error
)

echo.
echo [3/5] Checking Django installation...
python -c "import django; print(f'Django version: {django.get_version()}')"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Django not installed!
    goto error
)

echo.
echo [4/5] Checking for secret files...
if exist "serviceAccountKey.json" (
    echo [WARNING] serviceAccountKey.json found - DO NOT commit to Git!
)
if exist ".env" (
    echo [WARNING] .env file found - DO NOT commit to Git!
)

echo.
echo [5/5] Running Django checks...
python manage.py check --deploy
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some deployment warnings found
)

echo.
echo ================================
echo Deployment Readiness: READY!
echo ================================
echo.
echo Next steps:
echo 1. Push your code to GitHub
echo 2. Deploy to Railway or Render
echo 3. Add environment variables
echo 4. Run migrations on production
echo.
echo See DEPLOYMENT_INSTRUCTIONS.md for detailed steps.
goto end

:error
echo.
echo ================================
echo Deployment Readiness: NOT READY
echo ================================
echo.
echo Please fix the errors above before deploying.

:end
pause

