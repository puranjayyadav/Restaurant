# Get the Correct Connection String from Supabase Dashboard

The connection is failing because we need the **exact** connection string from your Supabase dashboard.

## Steps:

1. **Go to your Supabase Dashboard**:
   - https://supabase.com/dashboard/project/diytyziczzosylmyrfxo

2. **Click the "Connect" button** at the top of the page (or go to Settings → Database)

3. **Look for "Connection string" section**

4. **For Django/PostgreSQL clients, use "Session mode" (Supavisor)**:
   - This should show a connection string like:
   ```
   postgres://postgres.diytyziczzosylmyrfxo:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
   ```
   - **Important**: The region might be different (not necessarily us-east-1)
   - Common regions: `us-east-1`, `us-west-1`, `eu-west-1`, `ap-southeast-1`, etc.

5. **Copy the ENTIRE connection string** from the dashboard

6. **Update your `.env` file**:
   - Replace `DATABASE_URL` with the exact string from Supabase
   - Make sure to URL-encode your password if it has special characters
   - Your password `hArsh@1971RN` should be `hArsh%401971RN`

## What to Look For:

The connection string should have:
- ✅ Username: `postgres.diytyziczzosylmyrfxo` (with the project ref)
- ✅ Correct region in the hostname (e.g., `aws-0-us-east-1` or `aws-0-eu-west-1`)
- ✅ Port: `5432` for Session mode
- ✅ Password: URL-encoded if it has special characters

## After Updating:

Run the test again:
```bash
python test_supabase_connection.py
```

