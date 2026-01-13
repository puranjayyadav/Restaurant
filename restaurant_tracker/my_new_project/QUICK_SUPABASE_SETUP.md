# Quick Supabase Setup

## 1. Create Supabase Project
- Go to [supabase.com](https://supabase.com)
- Create new project
- Save your database password!

## 2. Get Connection String
- Dashboard → Settings → Database
- Copy "Connection string" (URI format)
- Replace `[YOUR-PASSWORD]` with your actual password

## 3. Set Environment Variable

### Option A: Create .env file (Recommended)
```bash
# In my_new_project/ directory
echo "DATABASE_URL=postgresql://postgres.xxx:your_password@xxx.supabase.co:5432/postgres?sslmode=require" > .env
```

### Option B: Export in terminal
```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres.xxx:your_password@xxx.supabase.co:5432/postgres?sslmode=require"

# Linux/Mac
export DATABASE_URL="postgresql://postgres.xxx:your_password@xxx.supabase.co:5432/postgres?sslmode=require"
```

## 4. Test Connection
```bash
cd my_new_project
python test_supabase_connection.py
```

## 5. Run Migrations
```bash
python manage.py migrate
```

## 6. Import Your Data
```bash
python manage.py import_scraped_restaurants ../nyc_restaurants_complete.json --source opentable
```

## Done! ✅

Your Django app is now connected to Supabase PostgreSQL.

## View Your Data
- Supabase Dashboard → Table Editor → `res_backend_scrapedrestaurant`
- Or Django Admin: http://localhost:8000/admin/

