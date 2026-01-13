import os
import django
import sys
from collections import Counter

# Set up Django environment
sys.path.append(r'c:\Users\PURANJAY\OneDrive\Documents\Res_2\my_new_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from res_backend.density_heatmap import create_grid_cells, calculate_grid_density

def diagnose_distribution():
    print("\n" + "="*70)
    print("DIAGNOSING CATEGORY DISTRIBUTION")
    print("="*70)
    
    # SoHo coordinates
    lat, lng = 40.7216, -74.0047
    grid_size = 0.008
    grid_count = 11
    
    # Generate cells
    cells = create_grid_cells(lat, lng, grid_size, grid_count)
    
    # Testing Vibe: 'all'
    print(f"\nTesting Vibe: 'all'")
    cells_with_density = calculate_grid_density(lat, lng, cells, vibe_filter='all')
    
    vibes = [c['vibe'] for c in cells_with_density]
    dist = Counter(vibes)
    
    print(f"Total cells above threshold: {len(cells_with_density)}")
    print("Vibe Distribution:")
    for vibe, count in dist.items():
        print(f"  {vibe}: {count} ({count/len(vibes)*100:.1f}%)")
    
    if cells_with_density:
        print("\nTop 5 Cells details:")
        sorted_cells = sorted(cells_with_density, key=lambda x: x['density_score'], reverse=True)
        for i, c in enumerate(sorted_cells[:5]):
            print(f"Cell {i+1}: {c['id']}")
            print(f"  Vibe: {c['vibe']}")
            print(f"  Score: {c['density_score']:.2f}")
            print(f"  Place Count: {c['place_count']}")

    print("\n" + "="*70)

if __name__ == "__main__":
    diagnose_distribution()
