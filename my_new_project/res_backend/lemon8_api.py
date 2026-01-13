import os
import json
import requests
from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from supabase import create_client
from decouple import config

def get_supabase_client():
    url = getattr(settings, 'SUPABASE_URL', os.getenv('SUPABASE_URL'))
    # Use service key for RPC/SQL if available, else standard key
    key = config('SUPABASE_SERVICE_ROLE_KEY', default=config('SUPABASE_SERVICE_KEY', default=getattr(settings, 'SUPABASE_KEY', '')))
    if not url or not key:
        return None
    return create_client(url, key)

@api_view(['POST'])
@permission_classes([])
def sql_extract_view(request):
    """
    Turns natural language into a safe SELECT query against lemon8_articles and executes it.
    """
    user_query = request.data.get('query')
    if not user_query:
        return Response({"error": "No query provided"}, status=status.HTTP_400_BAD_REQUEST)

    api_key = (getattr(settings, 'OPENROUTER_API_KEYv3', '') or 
              config('OPENROUTER_API_KEYv3', default='') or
              getattr(settings, 'OPENROUTER_API_KEY', '') or 
              config('OPENROUTER_API_KEY', default=''))
    model = config('OPENROUTER_CHAT_MODEL', default='xiaomi/mimo-v2-flash:free')
    
    system_prompt = f"""
    You are a PostgreSQL expert. Given a user question, generate a valid SELECT query.
    {LEMON8_SCHEMA_HINT}
    
    Rules:
    1. Only return the SQL query. No markdown formatting, no comments.
    2. Only SELECT statements are allowed.
    3. Only query the 'lemon8_articles' table.
    4. Use standard PostgreSQL syntax.
    """
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                "temperature": 0.0,
            },
            timeout=15
        )
        response.raise_for_status()
        sql_query = response.json()['choices'][0]['message']['content'].strip()
        
        # Clean up possible markdown or common LLM prefixes
        if sql_query.startswith("```sql"):
            sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
        elif sql_query.startswith("```"):
            sql_query = sql_query.split("```")[1].split("```")[0].strip()

        # Security: Basic check to ensure it's a SELECT and ONLY touches lemon8_articles
        sql_lower = sql_query.lower()
        if not sql_lower.startswith('select'):
             return Response({"error": "Only SELECT queries are allowed", "generated_sql": sql_query}, status=status.HTTP_403_FORBIDDEN)
             
        # Execute the query
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        return Response({
            "query": user_query,
            "generated_sql": sql_query,
            "results_count": len(rows),
            "results": rows
        })

    except Exception as e:
        return Response({
            "error": str(e), 
            "generated_sql": locals().get('sql_query', 'N/A')
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([])
def unified_generate_itinerary_view(request):
    """
    Unified endpoint for Flutter app - handles both query-based and location-based requests
    Directly implements the itinerary generation logic
    """
    try:
        from .day_planner_service import DayPlannerService
        
        # Extract parameters from Flutter app format
        data = request.data
        user_location = data.get('user_location', {})
        
        # Extract coordinates
        start_lat = user_location.get('lat') or data.get('start_lat') or data.get('latitude')
        start_long = user_location.get('lng') or data.get('start_long') or data.get('longitude')
        selected_vibe = data.get('selected_vibe')
        social_context = data.get('social_context') or 'couple'
        radius_meters = int(data.get('radius_meters', 3000))
        local_time_start = data.get('local_time_start', '10:00')
        cuisine_preferences = data.get('cuisine_preferences')
        cuisine_preference_min = data.get('cuisine_preference_min')
        cuisine_preference_max = data.get('cuisine_preference_max')
        
        # Apply defaults: randomize selected_vibe if null
        if selected_vibe is None:
            import random
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                try:
                    result = supabase.table("venue_vibes").select("vibe_slug").limit(100).execute()
                    if result.data:
                        available_vibes = list(set([v.get('vibe_slug') for v in result.data if v.get('vibe_slug')]))
                        if available_vibes:
                            selected_vibe = random.choice(available_vibes)
                except Exception as e:
                    print(f"Could not fetch vibes for randomization: {e}")
                    common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                    selected_vibe = random.choice(common_vibes)
            else:
                common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                selected_vibe = random.choice(common_vibes)
        
        # Convert to float only if provided
        start_lat = float(start_lat) if start_lat is not None else None
        start_long = float(start_long) if start_long is not None else None
        
        # Validate social_context
        valid_contexts = ['couple', 'solo', 'group', 'family']
        if social_context not in valid_contexts:
            return Response(
                {"error": f"social_context must be one of: {', '.join(valid_contexts)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate itinerary
        planner = DayPlannerService()
        result = planner.generate_itinerary(
            start_lat=start_lat,
            start_long=start_long,
            selected_vibe=selected_vibe,
            social_context=social_context,
            radius_meters=radius_meters,
            local_time_start=local_time_start,
            cuisine_preferences=cuisine_preferences,
            cuisine_preference_min=cuisine_preference_min,
            cuisine_preference_max=cuisine_preference_max
        )
        
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"ERROR: unified generateItinerary: {str(e)}")
        traceback.print_exc()
        return Response({
            "error": str(e),
            "message": "Failed to generate itinerary"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([])
def semantic_search_view(request):
    """
    Creates embeddings via OpenRouter and calls Supabase match_lemon8_articles RPC.
    """
    query = request.data.get('query')
    k = request.data.get('k', 5)
    threshold = request.data.get('threshold', 0.2)
    
    if not query:
        return Response({"error": "No query provided"}, status=status.HTTP_400_BAD_REQUEST)

    api_key = (getattr(settings, 'OPENROUTER_API_KEYv3', '') or 
              config('OPENROUTER_API_KEYv3', default='') or
              getattr(settings, 'OPENROUTER_API_KEY', '') or 
              config('OPENROUTER_API_KEY', default=''))
    embedding_model = config('OPENROUTER_EMBEDDING_MODEL', default='text-embedding-3-small')
    
    try:
        # 1. Create embedding
        emb_res = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": embedding_model,
                "input": query
            },
            timeout=10
        )
        emb_res.raise_for_status()
        embedding = emb_res.json()['data'][0]['embedding']
        
        # 2. Call Supabase RPC
        supabase = get_supabase_client()
        if not supabase:
            return Response({"error": "Supabase client not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        rpc_res = supabase.rpc('match_lemon8_articles', {
            'query_embedding': embedding,
            'match_threshold': threshold,
            'match_count': k
        }).execute()
        
        return Response({
            "query": query,
            "results": rpc_res.data
        })

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
