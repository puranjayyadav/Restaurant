"""Test Supabase connection and database setup"""
import os
from supabase_config import get_supabase_client, get_queue_stats

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_connection():
    """Test Supabase connection"""
    print("=" * 60)
    print("Testing Supabase Connection")
    print("=" * 60)
    print()
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url:
        print("⚠ SUPABASE_URL not found in environment variables")
        print("Make sure you have a .env file or set the environment variable")
        return False
    
    if not supabase_key:
        print("⚠ SUPABASE_KEY not found in environment variables")
        print("Make sure you have a .env file or set the environment variable")
        return False
    
    print(f"✓ SUPABASE_URL: {supabase_url[:30]}...")
    print(f"✓ SUPABASE_KEY: {supabase_key[:30]}...")
    print()
    
    # Test connection
    print("Connecting to Supabase...")
    client = get_supabase_client()
    
    if not client:
        print("✗ Failed to create Supabase client")
        return False
    
    print("✓ Supabase client created")
    print()
    
    # Test queue stats
    print("Testing database connection...")
    try:
        stats = get_queue_stats()
        if stats is not None:
            print("✓ Database connection successful!")
            print()
            print("Queue Statistics:")
            print(f"  Pending: {stats.get('pending', 0)}")
            print(f"  Processing: {stats.get('processing', 0)}")
            print(f"  Completed: {stats.get('completed', 0)}")
            print(f"  Failed: {stats.get('failed', 0)}")
            return True
        else:
            print("⚠ Could not get queue stats (tables might not exist yet)")
            print("Run supabase_schema.sql in your Supabase SQL Editor")
            return False
    except Exception as e:
        print(f"✗ Error testing database: {e}")
        print()
        print("This might mean:")
        print("  1. Database tables don't exist yet (run supabase_schema.sql)")
        print("  2. Wrong credentials")
        print("  3. Network issue")
        return False

if __name__ == "__main__":
    success = test_connection()
    print()
    print("=" * 60)
    if success:
        print("✓ All tests passed! You're ready to use the crawler.")
    else:
        print("✗ Some tests failed. Check the messages above.")
    print("=" * 60)
