# How to Configure Supabase URL and Key

## Step 1: Get Your Supabase Credentials

1. Go to https://supabase.com and log in
2. Select your project (or create a new one)
3. Go to **Settings** → **API** (in the left sidebar)
4. You'll see two values you need:

### SUPABASE_URL
- Look for **"Project URL"** or **"API URL"**
- Format: `https://xxxxx.supabase.co`
- Example: `https://abcdefghijklmnop.supabase.co`
- ⚠️ **NOT** the PostgreSQL connection string!

### SUPABASE_KEY
- Look for **"anon"** or **"public"** key
- This is a long JWT token starting with `eyJ...`
- Use the **anon/public** key (not the service_role key)

## Step 2: Configure Locally (for testing)

### Option A: Create `.env` file (Recommended)

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```bash
   SUPABASE_URL=https://abcdefghijklmnop.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   OPENROUTER_API_KEY=sk-or-v1-...
   ```

3. The scripts will automatically load from `.env` file

### Option B: Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:SUPABASE_URL="https://xxxxx.supabase.co"
$env:SUPABASE_KEY="eyJhbGc..."
$env:OPENROUTER_API_KEY="sk-or-v1-..."
```

**Windows (CMD):**
```cmd
set SUPABASE_URL=https://xxxxx.supabase.co
set SUPABASE_KEY=eyJhbGc...
set OPENROUTER_API_KEY=sk-or-v1-...
```

**Linux/Mac:**
```bash
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="eyJhbGc..."
export OPENROUTER_API_KEY="sk-or-v1-..."
```

## Step 3: Configure for GitHub Actions (for automation)

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these three secrets:

   - **Name:** `SUPABASE_URL`  
     **Value:** `https://xxxxx.supabase.co`

   - **Name:** `SUPABASE_KEY`  
     **Value:** `eyJhbGc...` (the anon/public key)

   - **Name:** `OPENROUTER_API_KEY`  
     **Value:** `sk-or-v1-...`

5. The GitHub Actions workflow will automatically use these secrets

## Step 4: Verify Configuration

Test your configuration:

```python
from supabase_config import get_supabase_client, get_queue_stats

# Test connection
client = get_supabase_client()
if client:
    print("✓ Supabase connected!")
    
    # Test queue stats
    stats = get_queue_stats()
    print(f"Queue stats: {stats}")
else:
    print("✗ Failed to connect. Check your SUPABASE_URL and SUPABASE_KEY")
```

Or run the scout script:
```bash
python scout_lemon8.py "https://www.lemon8-app.com/experience/new-york-eat?region=us"
```

## Common Mistakes

❌ **Wrong:** Using PostgreSQL connection string
```
SUPABASE_URL=postgres://postgres.xxx:password@xxx:5432/postgres
```

✅ **Correct:** Using Supabase Project URL
```
SUPABASE_URL=https://xxxxx.supabase.co
```

❌ **Wrong:** Using service_role key (too powerful, security risk)
```
SUPABASE_KEY=eyJ... (service_role key)
```

✅ **Correct:** Using anon/public key
```
SUPABASE_KEY=eyJ... (anon/public key)
```

## Where to Find in Supabase Dashboard

1. **Project URL:**
   - Settings → API → Project URL
   - Or: Settings → General → Reference ID (add `.supabase.co`)

2. **Anon Key:**
   - Settings → API → Project API keys → `anon` `public`
   - This is the key that starts with `eyJ...`

## Security Notes

- ✅ **anon/public key** is safe to use in client-side code and GitHub Actions
- ❌ **service_role key** should NEVER be exposed (has admin access)
- ✅ Store secrets in GitHub Secrets (encrypted)
- ✅ Use `.env` file locally (add to `.gitignore`)
