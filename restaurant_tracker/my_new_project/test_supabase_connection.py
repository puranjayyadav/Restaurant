"""
Test script to verify Supabase PostgreSQL connection
Run this after setting up your DATABASE_URL environment variable or .env file
"""
import os
import sys
import django
from decouple import config

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from django.db import connection
from django.conf import settings

def test_connection():
    """Test database connection"""
    print("=" * 60)
    print("Testing Supabase PostgreSQL Connection")
    print("=" * 60)
    
    # Check if DATABASE_URL is set (from .env file or environment variable)
    database_url = config('DATABASE_URL', default=None)
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("\nTo set it:")
        print("1. Create a .env file in my_new_project/ directory")
        print("2. Add: DATABASE_URL=postgresql://...")
        print("3. Or export it: export DATABASE_URL=postgresql://...")
        return False
    
    # Mask password in URL for display
    if '@' in database_url:
        parts = database_url.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split('://')[1] if '://' in parts[0] else parts[0]
            if ':' in user_pass:
                user, _ = user_pass.split(':', 1)
                masked_url = database_url.replace(user_pass, f"{user}:***")
            else:
                masked_url = database_url
        else:
            masked_url = database_url
    else:
        masked_url = database_url
    
    print(f"\n📋 Database URL: {masked_url}")
    print(f"📋 Database Engine: {settings.DATABASES['default']['ENGINE']}")
    
    # Test connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"\n✅ Connection successful!")
            print(f"📊 PostgreSQL Version: {version}")
            
            # Get database name
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            print(f"📊 Database Name: {db_name}")
            
            # Check if our tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if tables:
                print(f"\n📋 Existing Tables ({len(tables)}):")
                for table in tables[:10]:  # Show first 10
                    print(f"   - {table[0]}")
                if len(tables) > 10:
                    print(f"   ... and {len(tables) - 10} more")
            else:
                print("\n⚠️  No tables found. Run migrations:")
                print("   python manage.py migrate")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Connection failed!")
        print(f"Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check your DATABASE_URL format")
        print("2. Verify your Supabase password is correct")
        print("3. Ensure SSL mode is set: ?sslmode=require")
        print("4. Check if your IP is allowed in Supabase dashboard")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

