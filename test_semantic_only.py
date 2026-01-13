#!/usr/bin/env python3
"""Test semantic search directly"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'my_new_project'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from res_backend.hybrid_search_service import HybridSearchService

service = HybridSearchService()

# Test query
query = "romantic Indian dinner"
print(f"Testing query: '{query}'")
print("="*60)

# Generate query embedding
query_embedding = service.embedding_service.generate_embedding(query)
if query_embedding:
    print(f"Query embedding generated: {len(query_embedding)} dimensions")
    print(f"First 5 values: {query_embedding[:5]}")
    
    # Test the Supabase RPC directly
    try:
        result = service.supabase.rpc('hybrid_search_venues', {
            'query_embedding': query_embedding,
            'vibe_slugs': ['dinner_date'],
            'cuisine_slugs': ['indian_north', 'indian_south'],
            'match_threshold': 0.3,
            'lat': 40.7489,
            'lng': -73.9680,
            'radius_km': 5.0,
            'limit_count': 10
        }).execute()
        
        print(f"\nSupabase RPC returned: {len(result.data) if result.data else 0} results")
        if result.data:
            print("\nTop 3 results:")
            for i, venue in enumerate(result.data[:3], 1):
                print(f"\n  {i}. {venue.get('name')}")
                print(f"     Semantic Score: {venue.get('semantic_score', 0):.3f}")
                print(f"     Vibe Match: {venue.get('vibe_match_score', 0):.3f}")
                print(f"     Final Score: {venue.get('final_score', 0):.3f}")
        else:
            print("\nNo results from Supabase RPC - this might mean:")
            print("  1. The hybrid_search_venues function doesn't exist (migration not applied)")
            print("  2. No venues with embeddings match the query")
            print("  3. The embeddings aren't in the correct format")
    except Exception as e:
        print(f"\nError calling Supabase RPC: {e}")
        print("\nThis likely means the migration hasn't been applied.")
        print("Please run supabase_migration_embeddings.sql in your Supabase SQL Editor.")
else:
    print("Failed to generate query embedding!")
