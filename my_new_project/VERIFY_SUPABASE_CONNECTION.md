# Verify Your Supabase Connection String

The connection is failing because the hostname cannot be resolved. Please verify your connection string from Supabase.

## Steps to Get the Correct Connection String:

1. **Go to Supabase Dashboard**: https://supabase.com/dashboard
2. **Select your project**
3. **Go to**: Settings → Database
4. **Scroll to "Connection string" section**
5. **Select "URI" tab** (not "JDBC" or "Golang")
6. **Copy the connection string**

## Common Connection String Formats:

### Direct Connection (Port 5432):
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

### Connection Pooling (Port 6543):
```
postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### With SSL (Required):
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres?sslmode=require
```

## Important Notes:

1. **Password Encoding**: If your password contains special characters like `@`, `#`, `%`, etc., they need to be URL-encoded:
   - `@` → `%40`
   - `#` → `%23`
   - `%` → `%25`
   - `&` → `%26`
   - `+` → `%2B`
   - `=` → `%3D`

2. **Your current password**: `hArsh@1971RN`
   - The `@` needs to be encoded as `%40`
   - So it becomes: `hArsh%401971RN`

3. **Check the hostname**: Make sure you're using the correct hostname from Supabase dashboard. It should look like:
   - `db.xxxxx.supabase.co` (direct connection)
   - OR `aws-0-us-east-1.pooler.supabase.com` (connection pooling)

## Update Your .env File:

Once you have the correct connection string from Supabase:

1. Open `my_new_project/.env`
2. Replace the `DATABASE_URL` line with your actual connection string
3. Make sure to URL-encode any special characters in the password
4. Save the file
5. Run: `python test_supabase_connection.py`

## Alternative: Use Connection Pooling

If direct connection doesn't work, try the connection pooling endpoint (port 6543) which is more reliable:

```
postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

You can find this in Supabase Dashboard → Settings → Database → Connection pooling

