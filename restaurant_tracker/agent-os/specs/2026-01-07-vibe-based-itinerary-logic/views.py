
@api_view(['POST'])
@permission_classes([])
def generate_vibe_itinerary(request):
    """
    Generate vibe-based itinerary with two flows:
    - Flow A (Quick Search): Random NYC neighborhood, ignores user location
    - Flow B (Contextual): User location-aware search
    """
    from .vibe_itinerary_solver import generate_vibe_based_itinerary
    
    try:
        data = request.data
        flow_type = data.get('flow_type')
        vibe_slug = data.get('vibe_slug')
        quick_filter = data.get('quick_filter')
        query = data.get('query')
        location = data.get('location')
        max_venues = data.get('max_venues', 4)
        
        if not flow_type:
            return Response(
                {"error": "Missing required field: flow_type"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f"[generate_vibe_itinerary] Flow: {flow_type}, Vibe: {vibe_slug}, Filter: {quick_filter}, Query: {query}")
        
        result = generate_vibe_based_itinerary(
            flow_type=flow_type,
            vibe_slug=vibe_slug,
            quick_filter=quick_filter,
            query=query,
            location=location,
            max_venues=max_venues
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        import traceback
        print(f"[generate_vibe_itinerary] Error: {str(e)}")
        print(f"[generate_vibe_itinerary] Traceback: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to generate vibe itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
