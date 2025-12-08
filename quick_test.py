"""Quick test to verify Supabase setup"""
import os
import sys

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    print("⚠ python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"⚠ Error loading .env: {e}")

# Check env vars
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

print(f"\nSUPABASE_URL: {'SET' if url else 'NOT SET'}")
print(f"SUPABASE_KEY: {'SET' if key else 'NOT SET'}")

if not url or not key:
    print("\n⚠ Environment variables not set!")
    print("Make sure .env file exists with SUPABASE_URL and SUPABASE_KEY")
    sys.exit(1)

# Test Supabase connection
try:
    from supabase_config import get_supabase_client, get_queue_stats
    
    print("\nTesting Supabase connection...")
    client = get_supabase_client()
    
    if client:
        print("✓ Supabase client created successfully!")
        
        # Test database
        stats = get_queue_stats()
        if stats:
            print("\n✓ Database connection successful!")
            print(f"  Pending: {stats.get('pending', 0)}")
            print(f"  Completed: {stats.get('completed', 0)}")
        else:
            print("\n⚠ Could not get stats - tables might not exist")
            print("Run supabase_schema.sql in Supabase SQL Editor")
    else:
        print("✗ Failed to create Supabase client")
        sys.exit(1)
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ All tests passed!")
