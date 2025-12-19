"""
Neighborhood Density Heatmap API
Provides endpoints for calculating place density and returning GeoJSON for visualization.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
import math
from typing import List, Dict, Tuple
try:
    from .geohash_cache import get_curated_places_from_lemon8
except ImportError:
    # Handle if called from outside the package structure during tests
    def get_curated_places_from_lemon8(lat, lon, radius_km): return []


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def density_to_color(density_score: float) -> str:
    """
    Map density score (0-100) to color hex code.
    Uses a gradient from light blue (low) to deep red (high).
    """
    if density_score >= 80:
        return "#D32F2F"  # Deep red
    elif density_score >= 60:
        return "#FF5722"  # Orange-red
    elif density_score >= 40:
        return "#FF9800"  # Orange
    elif density_score >= 20:
        return "#FFA726"  # Light orange
    else:
        return "#81C784"  # Light green


def calculate_opacity(density_score: float) -> float:
    """Calculate polygon opacity based on density (0.2 to 0.8)."""
    return min(0.8, max(0.2, 0.2 + (density_score / 100) * 0.6))


def create_grid_cells(center_lat: float, center_lng: float, 
                      grid_size: float = 0.01, 
                      grid_count: int = 15) -> List[Dict]:
    """
    Generate a grid of rectangular cells around a center point.
    
    Args:
        center_lat: Center latitude
        center_lng: Center longitude
        grid_size: Size of each grid cell in degrees (~1.1km at NYC latitude)
        grid_count: Number of grid cells in each direction from center
        
    Returns:
        List of grid cell dictionaries with bounds
    """
    cells = []
    half_grid = grid_count // 2
    
    for i in range(-half_grid, half_grid + 1):
        for j in range(-half_grid, half_grid + 1):
            min_lat = center_lat + (i * grid_size)
            max_lat = center_lat + ((i + 1) * grid_size)
            min_lng = center_lng + (j * grid_size)
            max_lng = center_lng + ((j + 1) * grid_size)
            
            cell_center_lat = (min_lat + max_lat) / 2
            cell_center_lng = (min_lng + max_lng) / 2
            
            cells.append({
                'id': f"cell_{i}_{j}",
                'bounds': {
                    'min_lat': min_lat,
                    'max_lat': max_lat,
                    'min_lng': min_lng,
                    'max_lng': max_lng
                },
                'center': {
                    'lat': cell_center_lat,
                    'lng': cell_center_lng
                }
            })
    
    return cells


def _normalize_category(raw_cat: str) -> str:
    """Helper to group detailed tags into 4 main buckets."""
    if not raw_cat: return 'food'
    raw = raw_cat.lower()
    if 'coffee' in raw or 'bakery' in raw or 'cafe' in raw or 'brunch' in raw: return 'coffee'
    if 'bar' in raw or 'club' in raw or 'speakeasy' in raw or 'cocktail' in raw or 'wine' in raw: return 'nightlife'
    if 'art' in raw or 'museum' in raw or 'gallery' in raw or 'park' in raw or 'culture' in raw or 'theater' in raw or 'landmark' in raw or 'music' in raw: return 'arts'
    return 'food'

def calculate_grid_density(lat: float, lng: float, 
                           cells: List[Dict], 
                           vibe_filter: str = None) -> List[Dict]:
    """
    Calculate Itinerary-Aware Vibe Gravity for each grid cell.
    Implements Diversity Capping and Weighting for the 'all' view.
    """
    # 1. Fetch Curated Data (Gravity Anchors)
    radius_km = 3.0 
    curated_places = get_curated_places_from_lemon8(lat, lng, radius_km)
    
    is_balanced_view = not vibe_filter or vibe_filter.lower() == 'all'
    
    # Weights for visual dominance in "Balanced" view
    vibe_weights = {
        'arts': 6.0,      # Rare gems glow brightest
        'nightlife': 2.5,  # Strong identity
        'coffee': 3.0,     # Morning anchors
        'food': 1.0        # High volume, lowered importance
    }
    
    # Capping thresholds for "Balanced" view
    vibe_caps = {
        'arts': 100,
        'nightlife': 80,
        'coffee': 70,
        'food': 35 # Aggressive cap for food to allow others to shine
    }
    
    vibe_keywords = {
        'coffee': ['Coffee', 'Bakery', 'Cafe', 'Breakfast', 'Brunch'],
        'nightlife': ['Bar', 'Club', 'Speakeasy', 'Lounge', 'Cocktail'],
        'food': ['Restaurant', 'Dining', 'Food', 'Dinner', 'Lunch'],
        'arts': ['Gallery', 'Museum', 'Art', 'Studio', 'Theater']
    }
    
    keywords = vibe_keywords.get(vibe_filter.lower(), []) if vibe_filter and not is_balanced_view else []
    
    valid_cells = []
    
    with connection.cursor() as cursor:
        for cell in cells:
            bounds = cell['bounds']
            
            # For Balanced View, we fetch high quality or curated only to prioritize "Best of"
            query = """
                SELECT 
                    categories::text,
                    rating,
                    price_range,
                    hours,
                    raw_data
                FROM res_backend_scrapedrestaurant
                WHERE latitude BETWEEN %s AND %s
                AND longitude BETWEEN %s AND %s
                AND is_active = true
            """
            params = [bounds['min_lat'], bounds['max_lat'], 
                     bounds['min_lng'], bounds['max_lng']]
            
            if keywords:
                filter_clause = " AND (" + " OR ".join(["categories::text ILIKE %s" for _ in keywords]) + ")"
                query += filter_clause
                params.extend([f'%{kw}%' for kw in keywords])
            elif is_balanced_view:
                # In balanced view, raise the bar: only show spots with high quality or curated data
                # Using source='lemon8' or high rating/quality score
                query += " AND (source = 'lemon8' OR rating >= 4.0 OR data_quality_score >= 80)"

            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
            except Exception as e:
                print(f"[ERROR] DB Query failed in cell {cell['id']}: {e}\nQuery: {query}\nParams: {params}")
                continue
            
            # Initial tracking for this cell
            cell_scores = {'coffee': 0, 'nightlife': 0, 'arts': 0, 'food': 0}
            total_places = 0
            
            # --- PROCESS DB VENUES ---
            try:
                for row in rows:
                    cat_str, rating, price, hours, raw_data = row
                    cat = _normalize_category(cat_str)
                    
                    # SATURATION CAPPING: If this category is already strong in this cell, skip it
                    if is_balanced_view and cell_scores[cat] >= vibe_caps.get(cat, 50):
                        continue
                    
                    # Scoring Logic
                    score = 0
                    if rating and rating >= 4.5: score += 15
                    elif rating and rating >= 4.0: score += 8
                    else: score += 2
                    
                    if price: score += 5
                    if hours and hours != '{}': score += 10
                    
                    # Apply Vibe Weight in Balanced View
                    if is_balanced_view:
                        score *= vibe_weights.get(cat, 1.0)

                    cell_scores[cat] += score
                    total_places += 1
            except Exception as e:
                print(f"[ERROR] Data processing failed in cell {cell['id']}: {e}")
                continue

            # --- PROCESS CURATED PLACES (Anchors) ---
            cell_curated_count = 0
            for cp in curated_places:
                if (bounds['min_lat'] <= cp['lat'] <= bounds['max_lat'] and 
                    bounds['min_lng'] <= cp['lng'] <= bounds['max_lng']):
                    
                    cell_curated_count += 1
                    # Curated vibe
                    raw_cp_cat = cp.get('categories', [''])[0] if cp.get('categories') else ''
                    cp_vibe = _normalize_category(raw_cp_cat)
                    
                    # Curated venues get huge boost, bypass capping if specific vibe selected
                    anchor_score = 100 if (not vibe_filter or vibe_filter.lower() == cp_vibe) else 50
                    
                    if cp_vibe in cell_scores:
                        # Apply capping to curated places as well in balanced view
                        if is_balanced_view and cell_scores[cp_vibe] >= vibe_caps.get(cp_vibe, 50):
                            continue
                        
                        inc = anchor_score
                        if is_balanced_view:
                            inc *= vibe_weights.get(cp_vibe, 1.0)
                        
                        cell_scores[cp_vibe] += inc
                    else:
                        cell_scores['food'] += anchor_score # Fallback
            
            total_gravity = sum(cell_scores.values())
            
            # THRESHOLDING
            if total_gravity < 30:
                continue

            # Determine Dominant Vibe for coloring
            # Priority tie-breaking: Arts > Nightlife > Coffee > Food
            vibe_priority = ['arts', 'nightlife', 'coffee', 'food']
            dominant_vibe = 'food'
            max_vibe_score = -1
            
            for v in vibe_priority:
                if cell_scores.get(v, 0) > max_vibe_score:
                    max_vibe_score = cell_scores[v]
                    dominant_vibe = v

            cell['place_count'] = total_places + cell_curated_count
            cell['density_score'] = total_gravity
            cell['vibe'] = dominant_vibe # Per-cell vibe
            cell['avg_rating'] = 4.5 if cell_curated_count > 0 else 4.2
            valid_cells.append(cell)
    
    if not valid_cells:
        return []

    # Normalize
    max_gravity = max([c['density_score'] for c in valid_cells], default=1.0)
    for cell in valid_cells:
        cell['density_score'] = min(100, (cell['density_score'] / max_gravity) * 100)
        cell['color'] = density_to_color(cell['density_score'])
        cell['opacity'] = calculate_opacity(cell['density_score'])
    
    return valid_cells


def cells_to_geojson(cells: List[Dict]) -> Dict:
    """
    Convert grid cells to GeoJSON FeatureCollection for flutter_map.
    
    Returns:
        GeoJSON FeatureCollection with polygon features
    """
    features = []
    
    for cell in cells:
        bounds = cell['bounds']
        
        # Create polygon coordinates (5 points to close the rectangle)
        coordinates = [[
            [bounds['min_lng'], bounds['min_lat']],  # SW
            [bounds['max_lng'], bounds['min_lat']],  # SE
            [bounds['max_lng'], bounds['max_lat']],  # NE
            [bounds['min_lng'], bounds['max_lat']],  # NW
            [bounds['min_lng'], bounds['min_lat']]   # Close polygon
        ]]
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': coordinates
            },
            'properties': {
                'id': cell['id'],
                'density_score': round(cell['density_score'], 2),
                'place_count': cell['place_count'],
                'avg_rating': round(cell['avg_rating'], 2),
                'color': cell['color'],
                'opacity': round(cell['opacity'], 2),
                'vibe': cell.get('vibe', 'food')
            }
        }
        
        features.append(feature)
    
    return {
        'type': 'FeatureCollection',
        'features': features
    }


@api_view(['GET'])
def get_density_heatmap(request):
    """
    Get neighborhood density heatmap as GeoJSON.
    """
    # Debug: Log incoming request
    print(f"\n[DEBUG] GET /api/neighborhoods/density/ - Params: {request.GET.dict()}")
    
    try:
        # Parse required parameters
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return Response({
            'error': 'Missing or invalid lat/lng parameters'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse optional parameters
    vibe = request.GET.get('vibe')
    category = request.GET.get('category')
    min_rating = request.GET.get('min_rating')
    if min_rating:
        try:
            min_rating = float(min_rating)
        except ValueError:
            min_rating = None
    
    grid_size = float(request.GET.get('grid_size', 0.01))
    grid_count = int(request.GET.get('grid_count', 15))
    
    # Generate grid cells
    cells = create_grid_cells(lat, lng, grid_size, grid_count)
    
    # Calculate density for each cell
    cells_with_density = calculate_grid_density(
        lat, lng,
        cells, 
        vibe_filter=vibe
    )
    
    # Convert to GeoJSON
    geojson = cells_to_geojson(cells_with_density)
    
    print(f"[DEBUG] Density Heatmap Generated: {len(geojson['features'])} cells found for vibe='{vibe}'")
    
    return Response(geojson, status=status.HTTP_200_OK)
