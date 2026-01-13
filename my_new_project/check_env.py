import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

print(f"OPENROUTER_API_KEY: {os.environ.get('OPENROUTER_API_KEY', 'MISSING')[:10]}...")
print(f"OPENROUTER_API_KEYv3: {os.environ.get('OPENROUTER_API_KEYv3', 'MISSING')[:10]}...")
print(f"SUPABASE_URL: {os.environ.get('SUPABASE_URL', 'MISSING')}")
print(f"DATABASE_URL exists: {'Yes' if os.environ.get('DATABASE_URL') else 'No'}")
print(f"BASE_DIR: {settings.BASE_DIR}")
print(f"Root Env exists: {os.path.exists(os.path.join(settings.BASE_DIR.parent, '.env'))}")
