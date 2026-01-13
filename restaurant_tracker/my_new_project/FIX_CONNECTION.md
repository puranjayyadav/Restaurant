# Fix Supabase Connection

## The Issue
Your connection string uses the direct connection hostname which only resolves to IPv6, causing connection issues on Windows.

## Solution: Use Connection Pooling

1. **Go to Supabase Dashboard**: https://supabase.com/dashboard/project/diytyziczzosylmyrfxo
2. **Navigate to**: Settings → Database
3. **Scroll to "Connection pooling"** section
4. **Copy the "Session" mode connection string** (port 6543)

The connection string should look like:
```
postgresql://postgres.diytyziczzosylmyrfxo:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

## Update Your .env File

1. Open `my_new_project/.env`
2. Replace the DATABASE_URL with the connection pooling string
3. **Important**: URL-encode your password:
   - `hArsh@1971RN` → `hArsh%401971RN` (the `@` becomes `%40`)

Your .env should have:
```
DATABASE_URL=postgresql://postgres.diytyziczzosylmyrfxo:hArsh%401971RN@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

## Test Connection

After updating, run:
```bash
python test_supabase_connection.py
```

## Alternative: Use MCP Server

Since the Supabase MCP server is working, you can also:
- Run migrations directly via MCP
- Execute SQL queries
- Manage your database

But for Django to work, you still need the correct connection string in your .env file.

