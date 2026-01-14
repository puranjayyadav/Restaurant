# Migrate lemon8_articles from Supabase to CockroachDB

This guide explains how to copy the `public.lemon8_articles` table from Supabase to CockroachDB.

## Prerequisites

1. **Install required Python packages:**
   ```bash
   pip install supabase psycopg2-binary python-decouple python-dotenv
   ```

2. **Get your Supabase credentials:**
   - Go to your Supabase dashboard
   - Settings → API
   - Copy `SUPABASE_URL` and `SUPABASE_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`)

3. **Get your CockroachDB connection string:**
   - Go to your CockroachDB cluster dashboard
   - Connection info → Connection string
   - Format: `postgresql://user:password@host:port/database?sslmode=verify-full`
   - **Download the SSL certificate** (required for `verify-full` mode)

## Setup

### Step 1: Download CockroachDB SSL Certificate

**Windows (PowerShell):**
```powershell
# Run the provided script
.\setup_cockroachdb_cert.ps1

# Or manually:
mkdir -p $env:appdata\postgresql\
Invoke-WebRequest -Uri https://cockroachlabs.cloud/clusters/5ce4244a-90f1-4a00-9b6b-da01d25d67c2/cert -OutFile $env:appdata\postgresql\root.crt
```

**Linux/Mac:**
```bash
mkdir -p ~/.postgresql
curl -o ~/.postgresql/root.crt https://cockroachlabs.cloud/clusters/5ce4244a-90f1-4a00-9b6b-da01d25d67c2/cert
```

### Step 2: Set Environment Variables

### Option 1: Environment Variables

Set the following environment variables:

```bash
# Supabase (source)
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"

# CockroachDB (destination)
export COCKROACHDB_URL="postgresql://puranjay:Mo4MAznbTMcufpVAsU6Yzw@tailed-okapi-20468.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full"
```

### Option 2: .env File

Create a `.env` file in the project root:

```env
# Supabase (source)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# CockroachDB (destination)
COCKROACHDB_URL=postgresql://puranjay:Mo4MAznbTMcufpVAsU6Yzw@tailed-okapi-20468.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full
```

**Important:** 
- URL-encode special characters in passwords (e.g., `@` → `%40`)
- Use the service role key for Supabase (not the anon key) to ensure full access

## Run Migration

```bash
python migrate_lemon8_to_cockroachdb.py
```

## What the Script Does

1. **Connects to Supabase** and fetches all records from `public.lemon8_articles`
2. **Connects to CockroachDB** using the provided connection string
3. **Creates the table schema** in CockroachDB (if it doesn't exist)
4. **Inserts all data** into CockroachDB with upsert logic (updates existing records)

## Table Schema

The script creates this table in CockroachDB:

```sql
CREATE TABLE public.lemon8_articles (
    url TEXT PRIMARY KEY,
    html_content TEXT,
    itinerary_data JSONB,
    enriched_itinerary_data JSONB,
    stops_lat DOUBLE PRECISION[],
    stops_lng DOUBLE PRECISION[],
    scraped_at TIMESTAMP,
    extracted_at TIMESTAMP,
    extraction_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Features

- **Batch processing**: Fetches and inserts data in batches for efficiency
- **Upsert logic**: Updates existing records if they already exist (based on `url` primary key)
- **Error handling**: Continues processing even if individual records fail
- **Progress tracking**: Shows progress during fetch and insert operations
- **Index creation**: Automatically creates indexes for better query performance

## Troubleshooting

### Connection Issues

**Supabase:**
- Verify your `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Make sure you're using the service role key (not anon key)

**CockroachDB:**
- Check that your connection string includes `?sslmode=require`
- Verify the host, port, database name, username, and password are correct
- Ensure your IP is whitelisted in CockroachDB (if required)

### Data Type Issues

- JSONB fields are automatically converted from strings to JSON objects
- Array fields (`stops_lat`, `stops_lng`) are preserved as arrays
- Timestamps are preserved as-is

### Performance

- For large datasets (>100k records), the script processes in batches
- Adjust `batch_size` parameters in the script if you encounter memory issues
- The script uses `execute_batch` for efficient bulk inserts

## Verification

After migration, verify the data:

```sql
-- In CockroachDB SQL shell
SELECT COUNT(*) FROM public.lemon8_articles;

-- Compare with Supabase
-- (Run in Supabase SQL editor)
SELECT COUNT(*) FROM public.lemon8_articles;
```

Both counts should match (or be close if new records were added during migration).
