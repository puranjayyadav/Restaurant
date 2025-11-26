# 📦 GitHub Setup & Push Guide

## Step-by-Step: Push Your Backend to GitHub

### Step 1: Create GitHub Repository

1. **Go to GitHub:** https://github.com
2. **Sign in** (or create account if you don't have one)
3. **Click the "+" icon** in top right → "New repository"
4. **Fill in details:**
   - **Repository name:** `food-explorer-backend` (or any name you like)
   - **Description:** "Django backend for Food Explorer app"
   - **Visibility:** Private (recommended) or Public
   - **DO NOT** initialize with README, .gitignore, or license
5. **Click "Create repository"**

### Step 2: Copy Your Repository URL

After creating, GitHub will show you a URL like:
```
https://github.com/YOUR-ACTUAL-USERNAME/food-explorer-backend.git
```

**Copy this URL!** You'll need it in the next step.

### Step 3: Initialize Git and Push

Open PowerShell in the `my_new_project` folder:

```powershell
cd C:\Users\PURANJAY\OneDrive\Documents\Res_2\my_new_project

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Django backend"

# Set main branch
git branch -M main

# Add your ACTUAL repository URL (replace with yours!)
git remote add origin https://github.com/YOUR-ACTUAL-USERNAME/food-explorer-backend.git

# Push to GitHub
git push -u origin main
```

**Replace `YOUR-ACTUAL-USERNAME` with your real GitHub username!**

---

## 🆘 Common Errors & Solutions

### Error: "failed to push some refs"

**Cause:** Using placeholder URL or wrong URL

**Solution:**
```powershell
# Remove wrong remote
git remote remove origin

# Add correct remote (use YOUR actual URL from GitHub)
git remote add origin https://github.com/YOURNAME/YOUR-REPO.git

# Try pushing again
git push -u origin main
```

---

### Error: "Repository not found"

**Cause:** Wrong username or repository name

**Solution:**
1. Check your GitHub repository URL
2. Make sure repository exists
3. Verify you're logged in to the correct GitHub account

---

### Error: "Authentication failed"

**Cause:** GitHub requires Personal Access Token (not password)

**Solution:**

#### Option A: Use GitHub Desktop (Easiest)
1. Download GitHub Desktop: https://desktop.github.com/
2. Sign in with your GitHub account
3. Add your local repository
4. Push from GitHub Desktop

#### Option B: Create Personal Access Token
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it "Backend deployment"
4. Check scope: `repo` (full control of private repositories)
5. Click "Generate token"
6. **Copy the token** (you won't see it again!)
7. When pushing, use token as password:
   - Username: your-github-username
   - Password: paste-your-token-here

---

### Error: "Updates were rejected"

**Cause:** Remote has changes you don't have locally

**Solution:**
```powershell
# Pull remote changes first
git pull origin main --allow-unrelated-histories

# Then push
git push -u origin main
```

---

## ✅ Verify It Worked

After successful push:
1. Go to your GitHub repository URL
2. You should see all your files!
3. Files like `manage.py`, `requirements.txt`, `Procfile` should be visible

---

## 🔒 Security Check

**Before pushing, make sure these files are in `.gitignore`:**

- [ ] `.env` files
- [ ] `serviceAccountKey.json`
- [ ] `db.sqlite3`
- [ ] `__pycache__/`
- [ ] `*.pyc`

Run this to check:
```powershell
# See what will be committed
git status

# If you see sensitive files, remove them:
git rm --cached filename
```

---

## 🎯 Quick Reference

```powershell
# Check current remote
git remote -v

# Change remote URL
git remote set-url origin https://github.com/USERNAME/REPO.git

# See git status
git status

# See commit history
git log --oneline

# Push to GitHub
git push origin main
```

---

## 📱 Alternative: Use GitHub Desktop

**Easier than command line!**

1. Download: https://desktop.github.com/
2. Install and sign in
3. File → Add Local Repository
4. Select your `my_new_project` folder
5. Click "Publish repository" button
6. Done! It handles everything automatically

---

## ➡️ After Successful Push

Once your code is on GitHub:

1. **Deploy to Railway:**
   - Go to https://railway.app
   - "Deploy from GitHub"
   - Select your repository
   - Done!

2. **Or Deploy to Render:**
   - Go to https://render.com
   - "New +" → "Web Service"
   - Connect GitHub
   - Select your repository
   - Done!

---

## 💡 Pro Tips

1. **Use GitHub Desktop** if command line feels complicated
2. **Never commit secrets** (API keys, passwords, tokens)
3. **Make your repo private** if it contains sensitive code
4. **Add a good README** explaining what the project does

---

Need help? Just ask! 🚀

