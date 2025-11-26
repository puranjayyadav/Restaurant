@echo off
echo ================================
echo GitHub Quick Push Helper
echo ================================
echo.

echo This script will help you push your code to GitHub.
echo.
echo First, make sure you've created a repository on GitHub.com
echo.
pause

echo.
echo Please enter your GitHub repository URL:
echo Example: https://github.com/yourusername/your-repo.git
echo.
set /p REPO_URL="Repository URL: "

if "%REPO_URL%"=="" (
    echo Error: No URL provided!
    pause
    exit /b 1
)

echo.
echo Using repository: %REPO_URL%
echo.
echo Initializing git...
git init

echo.
echo Adding files...
git add .

echo.
echo Committing...
git commit -m "Initial commit - Backend for Food Explorer"

echo.
echo Setting branch to main...
git branch -M main

echo.
echo Removing old remote (if exists)...
git remote remove origin 2>nul

echo.
echo Adding new remote...
git remote add origin %REPO_URL%

echo.
echo Pushing to GitHub...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================
    echo SUCCESS!
    echo ================================
    echo.
    echo Your code is now on GitHub!
    echo Repository: %REPO_URL%
    echo.
    echo Next steps:
    echo 1. Go to https://railway.app or https://render.com
    echo 2. Click "Deploy from GitHub"
    echo 3. Select your repository
    echo 4. Your backend will be live in minutes!
    echo.
) else (
    echo.
    echo ================================
    echo PUSH FAILED
    echo ================================
    echo.
    echo Common issues:
    echo 1. Wrong repository URL
    echo 2. Authentication failed (need GitHub token)
    echo 3. Repository doesn't exist
    echo.
    echo Solutions:
    echo - Check your repository URL is correct
    echo - Use GitHub Desktop instead: https://desktop.github.com
    echo - See GITHUB_SETUP_GUIDE.md for detailed help
    echo.
)

pause

