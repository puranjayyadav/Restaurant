import os
import django
import sys
from collections import Counter
from django.db import connection

# Set up Django environment
sys.path.append(r'c:\Users\PURANJAY\OneDrive\Documents\Res_2\my_new_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from res_backend.density_heatmap import create_grid_cells, _normalize_category

def diagnose_deep():
    print("\n" + "="*70)
    print("DEEP DIAGNOSIS: RAW CATEGORY DISTRIBUTION")
    print("="*70)
    
    # SoHo coordinates
    lat, lng = 40.7216, -74.0047
    grid_size = 0.008
    grid_count = 11
    cells = create_grid_cells(lat, lng, grid_size, grid_count)
    
    total_found = {'coffee': 0, 'nightlife': 0, 'arts': 0, 'food': 0}
    quality_found = {'coffee': 0, 'nightlife': 0, 'arts': 0, 'food': 0}
    
    with connection.cursor() as cursor:
        for cell in cells:
            bounds = cell['bounds']
            query = """
                SELECT categories::text, rating, data_quality_score, source
                FROM res_backend_scrapedrestaurant
                WHERE latitude BETWEEN %s AND %s
                AND longitude BETWEEN %s AND %s
                AND is_active = true
            """
            cursor.execute(query, [bounds['min_lat'], bounds['max_lat'], bounds['min_lng'], bounds['max_lng']])
            rows = cursor.fetchall()
            
            for row in rows:
                cat_str, rating, quality, source = row
                cat = _normalize_category(cat_str)
                total_found[cat] += 1
                
                # Current quality bar
                is_quality = (source == 'lemon8' or (rating and float(rating) >= 4.0) or (quality and quality >= 80))
                if is_quality:
                    quality_found[cat] += 1
                    
    print("\nTOTAL SPOTS IN GRID:")
    for cat, count in total_found.items():
        print(f"  {cat}: {count}")
        
    print("\nQUALITY SPOTS IN GRID (Meeting Filter):")
    for cat, count in quality_found.items():
        print(f"  {cat}: {count}")

    print("\n" + "="*70)

if __name__ == "__main__":
    diagnose_deep()
