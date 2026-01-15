"""
Collection API endpoints for accessing CockroachDB collection tables.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


def get_cockroachdb_connection():
    """
    Create and return a connection to CockroachDB.
    """
    conn_string = os.getenv("COCKROACHDB_URL", "")
    if not conn_string:
        raise RuntimeError("COCKROACHDB_URL environment variable is not set")
    
    return psycopg2.connect(conn_string)


@api_view(['GET'])
def get_collections(request):
    """
    GET /api/collections/
    
    Retrieve all collections from CockroachDB.
    
    Query Parameters:
    - user_id (optional): Filter collections by user ID
    - limit (optional): Limit number of results (default: 100)
    - offset (optional): Offset for pagination (default: 0)
    
    Returns:
    - List of collection objects
    """
    try:
        user_id = request.GET.get('user_id')
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        min_items = request.GET.get('min_items')
        if min_items:
            min_items = int(min_items)
        
        conn = get_cockroachdb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        if min_items:
            query = """
                SELECT c.*, count(*) as item_count
                FROM collections c
                JOIN collection_items ci ON c.id = ci.collection_id
                GROUP BY c.id, c.name, c.description, c.neighborhood, c.created_at
                HAVING count(*) >= %s
                ORDER BY c.created_at DESC
                LIMIT %s OFFSET %s
            """
            params = [min_items, limit, offset]
        else:
            query = "SELECT * FROM collections ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params = [limit, offset]
        
        cursor.execute(query, params)
        collections = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return Response({
            "collections": collections,
            "count": len(collections),
            "limit": limit,
            "offset": offset
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_collection_by_id(request, collection_id):
    """
    GET /api/collections/<collection_id>/
    
    Retrieve a single collection by ID.
    
    Returns:
    - Collection object with its items
    """
    try:
        conn = get_cockroachdb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get collection
        cursor.execute("SELECT * FROM collections WHERE id = %s", (collection_id,))
        collection = cursor.fetchone()
        
        if not collection:
            cursor.close()
            conn.close()
            return Response({
                "error": "Collection not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get collection items joined with restaurant info
        cursor.execute("""
            SELECT 
                ci.*, 
                ra.establishment as name,
                ra.cuisine,
                ra.primary_draw,
                ra.community_perception,
                ra.neighborhood,
                ra.vibe,
                ra.app_ready_description as summary
            FROM collection_items ci
            LEFT JOIN restaurant_analysis ra ON ci.restaurant_id::text = ra.id::text
            WHERE ci.collection_id = %s
        """, (collection_id,))
        items = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return Response({
            "collection": collection,
            "items": items,
            "item_count": len(items)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_collection_items(request):
    """
    GET /api/collection-items/
    
    Retrieve collection items.
    
    Query Parameters:
    - collection_id (optional): Filter by collection ID
    - place_id (optional): Filter by place ID
    - limit (optional): Limit number of results (default: 100)
    - offset (optional): Offset for pagination (default: 0)
    
    Returns:
    - List of collection item objects
    """
    try:
        collection_id = request.GET.get('collection_id')
        place_id = request.GET.get('place_id')
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        
        conn = get_cockroachdb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        query = "SELECT * FROM collection_items WHERE 1=1"
        params = []
        
        if collection_id:
            query += " AND collection_id = %s"
            params.append(collection_id)
        
        if place_id:
            query += " AND restaurant_id = %s"
            params.append(place_id)
        
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        items = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return Response({
            "items": items,
            "count": len(items),
            "limit": limit,
            "offset": offset
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_collection(request):
    """
    POST /api/collections/
    
    Create a new collection.
    
    Request Body:
    {
        "user_id": "string",
        "name": "string",
        "description": "string" (optional),
        "is_public": boolean (optional, default: false)
    }
    
    Returns:
    - Created collection object
    """
    try:
        data = request.data
        user_id = data.get('user_id')
        name = data.get('name')
        description = data.get('description', '')
        is_public = data.get('is_public', False)
        
        if not name:
            return Response({
                "error": "name is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        conn = get_cockroachdb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO collections (name, description, neighborhood, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING *
        """, (name, description, data.get('neighborhood', '')))
        
        collection = cursor.fetchone()
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return Response({
            "collection": collection
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def add_collection_item(request):
    """
    POST /api/collection-items/
    
    Add an item to a collection.
    
    Request Body:
    {
        "collection_id": "string",
        "place_id": "string",
        "notes": "string" (optional)
    }
    
    Returns:
    - Created collection item object
    """
    try:
        data = request.data
        collection_id = data.get('collection_id')
        place_id = data.get('place_id')
        notes = data.get('notes', '')
        
        if not collection_id or not place_id:
            return Response({
                "error": "collection_id and place_id are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        conn = get_cockroachdb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO collection_items (collection_id, restaurant_id)
            VALUES (%s, %s)
            RETURNING *
        """, (collection_id, place_id))
        
        item = cursor.fetchone()
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return Response({
            "item": item
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
def search_restaurants(request):
    """
    GET /api/restaurants/search/
    
    Search through restaurants in the restaurant_analysis table.
    
    Query Parameters:
    - q: Search query (searches establishment, cuisine, neighborhood, vibe)
    - cuisine: Filter by cuisine (exact)
    - neighborhood: Filter by neighborhood (exact)
    - limit: Limit results (default: 20)
    - offset: Offset for pagination (default: 0)
    
    Returns:
    - List of matching restaurant objects
    """
    try:
        q = request.GET.get('q', '').strip()
        cuisine = request.GET.get('cuisine')
        neighborhood = request.GET.get('neighborhood')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        conn = get_cockroachdb_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM restaurant_analysis WHERE 1=1"
        params = []
        
        if q:
            # Search across multiple fields
            query += """ AND (
                establishment ILIKE %s OR 
                cuisine ILIKE %s OR 
                neighborhood ILIKE %s OR 
                vibe ILIKE %s OR
                primary_draw ILIKE %s
            )"""
            search_pattern = f"%{q}%"
            params.extend([search_pattern] * 5)
            
        if cuisine:
            query += " AND cuisine ILIKE %s"
            params.append(f"%{cuisine}%")
            
        if neighborhood:
            query += " AND neighborhood ILIKE %s"
            params.append(f"%{neighborhood}%")
            
        query += " ORDER BY establishment LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        restaurants = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return Response({
            "query": q,
            "count": len(restaurants),
            "limit": limit,
            "offset": offset,
            "restaurants": restaurants
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
