#!/usr/bin/env python3
"""Check if venues have embeddings"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'my_new_project'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from res_backend.embedding_service import EmbeddingService

service = EmbeddingService()
if not service.supabase:
    print("ERROR: Supabase client not configured")
    sys.exit(1)

# Check how many venues have embeddings
result = service.supabase.table('venues').select('place_id, name, rating, embedding').not_.is_('embedding', 'null').limit(10).execute()

print(f"Venues with embeddings: {len(result.data)}")
if result.data:
    print("\nSample venues with embeddings:")
    for venue in result.data[:5]:
        print(f"  - {venue.get('name')} (rating: {venue.get('rating')})")
        print(f"    Embedding length: {len(venue.get('embedding', [])) if venue.get('embedding') else 0}")
else:
    print("\nNo venues found with embeddings!")
    print("You may need to run: python manage.py generate_embeddings --limit 500 --min-rating 4.0")

# Check total venues
total_result = service.supabase.table('venues').select('place_id', count='exact').execute()
print(f"\nTotal venues in database: {total_result.count if hasattr(total_result, 'count') else 'Unknown'}")
