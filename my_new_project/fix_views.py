
import os

file_path = 'res_backend/views.py'
if not os.path.exists(file_path):
    print(f'Error: {file_path} not found')
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Correct the corrupted error handling in parse_query if it exists
corrupted = '''    except Exception as e:
        import traceback
        print(f"ERROR: Venue search failed: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Search failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )'''

correct = '''    except Exception as e:
        import traceback
        print(f"ERROR: parse_query endpoint error: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to parse query: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )'''

if corrupted in content:
    content = content.replace(corrupted, correct)
    print('Corrected parse_query error handling.')

# Add search_venues if not already there
search_venues_code = '''

@api_view(['GET'])
@permission_classes([])
def search_venues(request):
    """
    Search for venues in the Supabase database.
    Searches across name, address, city, and categories fields.
    
    Query parameters:
        - q: Search query string (required)
        - limit: Maximum number of results (default: 50)
    """
    try:
        query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 50))
        
        if not query:
            return Response(
                {"error": "Search query 'q' parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()
            
            if not supabase:
                return Response(
                    {"error": "Supabase client not available"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        except ImportError:
            return Response(
                {"error": "Supabase configuration not found"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        response = (
            supabase.table('venues')
            .select('*')
            .or_(f"name.ilike.%{query}%,address.ilike.%{query}%,city.ilike.%{query}%,categories.ilike.%{query}%")
            .order('rating', desc=True)
            .limit(limit)
            .execute()
        )
        
        venues = response.data if response.data else []
        
        print(f"DEBUG: Venue search for '{query}' returned {len(venues)} results")
        
        return Response({
            "query": query,
            "count": len(venues),
            "venues": venues
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"ERROR: Venue search failed: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Search failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
'''

if 'def search_venues(request):' not in content:
    content = content.strip() + search_venues_code
    print('Appended search_venues function.')
else:
    print('search_venues function already exists.')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('views.py update complete.')
