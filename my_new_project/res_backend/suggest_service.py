
import requests
from typing import List

def get_address_suggestions(query: str) -> List[str]:
    """
    Fetch address suggestions from OpenStreetMap (via Photon API).
    Photon is a high-performance search-as-you-type API powered by OSM data.
    """
    if not query or len(query) < 2:
        return []
        
    # Photon API endpoint
    url = f"https://photon.komoot.io/api/?q={query}&limit=8"
    
    headers = {
        'User-Agent': 'ResTripWizard/1.0 (Contact: support@example.com)',
        'Accept': 'application/json',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            suggestions = []
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                name = props.get('name')
                city = props.get('city')
                state = props.get('state')
                country = props.get('country')
                
                # Build a clean display string
                parts = []
                if name: parts.append(name)
                if city and city != name: parts.append(city)
                if state: parts.append(state)
                if country: parts.append(country)
                
                display_string = ", ".join(parts)
                if display_string:
                    suggestions.append(display_string)
            
            return list(dict.fromkeys(suggestions)) # Deduplicate while preserving order
            
    except Exception as e:
        print(f"ERROR: Failed to fetch OSM address suggestions for '{query}': {e}")
        
    return []
