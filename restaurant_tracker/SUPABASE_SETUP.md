# Supabase PostgreSQL Setup Guide

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click "New Project"
3. Fill in:
   - **Project Name**: `food-explorer` (or your preferred name)
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose closest to your users
   - **Pricing Plan**: Free tier is fine to start
4. Click "Create new project" (takes 1-2 minutes)

## Step 2: Get Connection String

1. In your Supabase project dashboard, go to **Settings** → **Database**
2. Scroll down to **Connection string** section
3. Select **URI** tab
4. Copy the connection string (looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with the password you created in Step 1

**Full connection string format:**
```
postgresql://postgres.xxxxxxxxxxxxx:your_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

## Step 3: Set Environment Variable

### For Local Development:

Create a `.env` file in `my_new_project/` directory:

```env
DATABASE_URL=postgresql://postgres.xxxxxxxxxxxxx:your_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
DEBUG=True
SECRET_KEY=your-secret-key-here
```

### For Production (Railway/Render/etc.):

Add `DATABASE_URL` as an environment variable in your hosting platform:
- Railway: Project → Service → Variables → Add `DATABASE_URL`
- Render: Environment → Add `DATABASE_URL`

## Step 4: Update Django Settings

Your `settings_prod.py` already uses `dj-database_url`, so it will automatically use the `DATABASE_URL` environment variable.

For local development, you can also use Supabase by setting the environment variable.

## Step 5: Run Migrations

```bash
cd my_new_project
python manage.py migrate
```

## Step 6: Import Your Data

```bash
python manage.py import_scraped_restaurants ../nyc_restaurants_complete.json --source opentable
```

## Step 7: Verify Connection

Test the connection:

```bash
python manage.py dbshell
```

You should see a PostgreSQL prompt if connected successfully.

## Supabase Dashboard Features

Once connected, you can:
- View your tables in **Table Editor**
- Run SQL queries in **SQL Editor**
- Monitor database usage in **Database** → **Usage**
- Set up backups in **Database** → **Backups**

## Connection Pooling (Recommended)

Supabase offers connection pooling. Use the **Session** mode connection string for Django:

1. Go to **Settings** → **Database**
2. Under **Connection string**, select **Session mode** (not Transaction mode)
3. Use port **5432** (not 6543) for direct connections

## Free Tier Limits

- **Database Size**: 500 MB
- **Bandwidth**: 5 GB/month
- **API Requests**: 50,000/month
- **Concurrent Connections**: 60

For your restaurant database, this should be sufficient to start!

## Troubleshooting

### Connection Timeout
- Check your firewall settings
- Ensure you're using the correct port (5432 for direct, 6543 for pooling)
- Verify SSL mode is set: `?sslmode=require`

### Authentication Failed
- Double-check your password (no spaces, special characters properly encoded)
- Make sure you're using the correct connection string format

### SSL Required
Supabase requires SSL. Make sure your connection string includes `?sslmode=require`

## Next Steps

1. Set up database backups (Supabase auto-backups on paid plans)
2. Monitor usage in Supabase dashboard
3. Consider upgrading if you exceed free tier limits

