# Add this to the end of views.py

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
            .or_(f'name.ilike.%{query}%,address.ilike.%{query}%,city.ilike.%{query}%,categories.ilike.%{query}%')
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
