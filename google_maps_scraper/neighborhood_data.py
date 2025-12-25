
"""
Hardcoded coordinates for NYC neighborhoods to ensure robust scraping 
without relying on Google Maps API or fragile HTML parsing.
"""

def get_neighborhood_viewport(neighborhood_name):
    """
    Returns a viewport dictionary {'northeast': {...}, 'southwest': {...}} 
    for a given neighborhood name.
    
    The scrape requires a viewport to generate a grid.
    We approximate a box around the center coordinate (~1.5km x 1.5km).
    """
    
    # Normalize input
    name_clean = neighborhood_name.split(',')[0].strip()
    
    # Center coordinates (Lat, Lng)
    centers = {
        # Manhattan South
        "Financial District": (40.7077, -74.0083),
        "Tribeca": (40.7163, -74.0086),
        "SoHo": (40.7233, -74.0030),
        "Little Italy": (40.7191, -73.9973),
        "Chinatown": (40.7158, -73.9970),
        "Lower East Side": (40.7150, -73.9890),
        "East Village": (40.7265, -73.9815),
        "West Village": (40.7358, -74.0036),
        "Greenwich Village": (40.7336, -74.0027),
        
        # Manhattan Mid
        "Chelsea": (40.7465, -74.0014),
        "Meatpacking District": (40.7410, -74.0076),
        "Flatiron District": (40.7411, -73.9897),
        "Gramercy Park": (40.7370, -73.9859),
        "Midtown West": (40.7633, -73.9904),
        "Hell's Kitchen": (40.7638, -73.9918),
        "Koreatown": (40.7477, -73.9869),
        "Murray Hill": (40.7479, -73.9757),
        
        # Brooklyn
        "Williamsburg": (40.7128, -73.9610),
        "Greenpoint": (40.7245, -73.9482),
        "DUMBO": (40.7031, -73.9896),
        "Brooklyn Heights": (40.6960, -73.9933),
        "Cobble Hill": (40.6874, -73.9945),
        "Bushwick": (40.7009, -73.9242),
        "Bed-Stuy": (40.6872, -73.9418),
        
        # Queens
        "Long Island City": (40.7484, -73.9480),
        "Astoria": (40.7644, -73.9235),
        "Sunnyside": (40.7433, -73.9196),
        "Jackson Heights": (40.7557, -73.8831),
        "Flushing": (40.7674, -73.8331)
    }
    
    if name_clean not in centers:
        return None
        
    lat, lng = centers[name_clean]
    
    # Create a bounding box (roughly +/- 0.01 deg is ~1.1km radius)
    delta = 0.012 
    
    return {
        'northeast': {'lat': lat + delta, 'lng': lng + delta},
        'southwest': {'lat': lat - delta, 'lng': lng - delta}
    }
