"""Test if .env file is being loaded"""
import os
import sys

print("Testing .env file loading...")
print(f"Current directory: {os.getcwd()}")

# Try to load .env
try:
    from dotenv import load_dotenv
    result = load_dotenv()
    print(f"load_dotenv() returned: {result}")
except ImportError:
    print("ERROR: python-dotenv not installed!")
    print("Run: pip install python-dotenv")
    sys.exit(1)

# Check if .env file exists
env_path = os.path.join(os.getcwd(), '.env')
print(f".env file path: {env_path}")
print(f".env file exists: {os.path.exists(env_path)}")

# Check environment variables
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

print(f"\nSUPABASE_URL: {'SET (' + url[:30] + '...)' if url else 'NOT SET'}")
print(f"SUPABASE_KEY: {'SET (' + key[:30] + '...)' if key else 'NOT SET'}")

if not url or not key:
    print("\n⚠️  Environment variables not loaded!")
    print("Make sure .env file exists in the current directory")
else:
    print("\n✓ Environment variables loaded successfully!")
