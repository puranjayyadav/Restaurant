#!/usr/bin/env python3
"""Test if embeddings can be queried directly"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'my_new_project'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from res_backend.embedding_service import EmbeddingService

service = EmbeddingService()

# Check how many venues have embeddings
result = service.supabase.table('venues').select('place_id, name').not_.is_('embedding', 'null').limit(5).execute()

print(f"Venues with embeddings: {len(result.data)}")
if result.data:
    print("\nTesting simple vector similarity query...")
    
    # Get one venue's embedding
    test_venue = result.data[0]
    venue_result = service.supabase.table('venues').select('place_id, name, embedding').eq('place_id', test_venue['place_id']).single().execute()
    
    if venue_result.data and venue_result.data.get('embedding'):
        embedding = venue_result.data['embedding']
        print(f"Found embedding for {venue_result.data['name']}")
        print(f"Embedding type: {type(embedding)}")
        print(f"Embedding length: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
        
        # Try a simple similarity query
        try:
            # Generate a test query embedding
            query_embedding = service.generate_embedding("romantic dinner")
            if query_embedding:
                print(f"\nQuery embedding generated: {len(query_embedding)} dimensions")
                
                # Try a simple RPC call with minimal parameters
                print("\nTesting simplified RPC call...")
                simple_result = service.supabase.rpc('hybrid_search_venues', {
                    'query_embedding': query_embedding,
                    'vibe_slugs': [],
                    'cuisine_slugs': [],
                    'match_threshold': 0.1,  # Lower threshold
                    'lat': None,
                    'lng': None,
                    'radius_km': 100.0,  # Large radius
                    'limit_count': 5  # Small limit
                }).execute()
                
                print(f"RPC returned: {len(simple_result.data) if simple_result.data else 0} results")
                if simple_result.data:
                    for venue in simple_result.data[:3]:
                        print(f"  - {venue.get('name')}: semantic={venue.get('semantic_score', 0):.3f}")
            else:
                print("Failed to generate query embedding")
        except Exception as e:
            print(f"Error: {e}")
            print("\nThe function might be too complex or the index isn't working.")
            print("Try checking if the vector index was created:")
            print("  SELECT * FROM pg_indexes WHERE tablename = 'venues' AND indexname LIKE '%embedding%';")
    else:
        print("No embedding found for test venue")
else:
    print("No venues with embeddings found!")
