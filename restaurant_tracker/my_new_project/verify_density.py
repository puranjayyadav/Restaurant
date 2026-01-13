import os
import django
import sys

# Set up Django environment
sys.path.append(r'c:\Users\PURANJAY\OneDrive\Documents\Res_2\my_new_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from res_backend.density_heatmap import create_grid_cells, calculate_grid_density

def verify_logic():
    print("\n" + "="*70)
    print("VERIFYING ITINERARY-AWARE HEATMAP LOGIC")
    print("="*70)
    
    # SoHo coordinates
    lat, lng = 40.7216, -74.0047
    grid_size = 0.008
    grid_count = 11
    
    # Generate cells
    cells = create_grid_cells(lat, lng, grid_size, grid_count)
    print(f"Generated {len(cells)} base cells.")
    
    # Test 1: Coffee vibe
    print(f"\nTesting Vibe: 'coffee'")
    cells_with_density = calculate_grid_density(lat, lng, cells, vibe_filter='coffee')
    print(f"Cells above threshold (Score >= 30): {len(cells_with_density)}")
    
    if cells_with_density:
        top_cell = max(cells_with_density, key=lambda x: x['density_score'])
        print(f"Top Cell Gravity Score: {top_cell['density_score']:.2f}")
        print(f"Top Cell Place Count: {top_cell['place_count']}")
    
    # Test 2: Nightlife vibe
    print(f"\nTesting Vibe: 'nightlife'")
    cells_with_density = calculate_grid_density(lat, lng, cells, vibe_filter='nightlife')
    print(f"Cells above threshold (Score >= 30): {len(cells_with_density)}")
    
    # Test 3: Non-existent vibe or broad vibe
    print(f"\nTesting Vibe: 'all'")
    cells_with_density = calculate_grid_density(lat, lng, cells, vibe_filter='all')
    print(f"Cells above threshold (Score >= 30): {len(cells_with_density)}")

    print("\n" + "="*70)

if __name__ == "__main__":
    verify_logic()
