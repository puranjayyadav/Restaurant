import json

with open('nyc_restaurants_complete.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total restaurants: {len(data)}\n")

# Analyze fields
cuisines = {}
neighborhoods = {}
price_ranges = {}
tags_all = {}
dining_styles = {}
has_menu = 0
has_reviews = 0
has_images = 0

for r in data:
    # Cuisine
    c = r.get('cuisine', 'Unknown')
    cuisines[c] = cuisines.get(c, 0) + 1
    
    # Neighborhood
    n = r.get('details', {}).get('neighborhood', 'Unknown')
    neighborhoods[n] = neighborhoods.get(n, 0) + 1
    
    # Price
    p = r.get('details', {}).get('price', 'Unknown')
    price_ranges[p] = price_ranges.get(p, 0) + 1
    
    # Dining style
    ds = r.get('details', {}).get('dining_style', 'Unknown')
    dining_styles[ds] = dining_styles.get(ds, 0) + 1
    
    # Tags
    for tag in r.get('tags', []):
        tags_all[tag] = tags_all.get(tag, 0) + 1
    
    # Count features
    if r.get('menu_items') and len(r.get('menu_items', [])) > 0:
        has_menu += 1
    if r.get('reviews') and len(r.get('reviews', [])) > 0:
        has_reviews += 1
    if r.get('images') and len(r.get('images', [])) > 1:  # More than just placeholder
        has_images += 1

print("=" * 60)
print("DATA AVAILABILITY:")
print("=" * 60)
print(f"Restaurants with menu items: {has_menu} ({has_menu/len(data)*100:.1f}%)")
print(f"Restaurants with reviews: {has_reviews} ({has_reviews/len(data)*100:.1f}%)")
print(f"Restaurants with images: {has_images} ({has_images/len(data)*100:.1f}%)")

print("\n" + "=" * 60)
print("TOP 10 CUISINES:")
print("=" * 60)
for k, v in sorted(cuisines.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {k}: {v}")

print("\n" + "=" * 60)
print("TOP 10 NEIGHBORHOODS:")
print("=" * 60)
for k, v in sorted(neighborhoods.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {k}: {v}")

print("\n" + "=" * 60)
print("PRICE RANGES:")
print("=" * 60)
for k, v in sorted(price_ranges.items(), key=lambda x: x[1], reverse=True):
    print(f"  {k}: {v}")

print("\n" + "=" * 60)
print("DINING STYLES:")
print("=" * 60)
for k, v in sorted(dining_styles.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {k}: {v}")

print("\n" + "=" * 60)
print("TOP 15 TAGS:")
print("=" * 60)
for k, v in sorted(tags_all.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f"  {k}: {v}")

# Sample restaurant with rich data
print("\n" + "=" * 60)
print("SAMPLE RESTAURANT WITH RICH DATA:")
print("=" * 60)
sample = None
for r in data:
    if (r.get('menu_items') and len(r.get('menu_items', [])) > 5 and 
        r.get('reviews') and len(r.get('reviews', [])) > 3 and
        r.get('images') and len(r.get('images', [])) > 3):
        sample = r
        break

if sample:
    print(f"Name: {sample['name']}")
    print(f"Cuisine: {sample.get('cuisine')}")
    print(f"Neighborhood: {sample.get('details', {}).get('neighborhood')}")
    print(f"Price: {sample.get('details', {}).get('price')}")
    print(f"Dining Style: {sample.get('details', {}).get('dining_style')}")
    print(f"Rating: {sample.get('rating')} ({sample.get('review_count')} reviews)")
    print(f"Tags: {', '.join(sample.get('tags', [])[:5])}")
    print(f"Menu Items: {len(sample.get('menu_items', []))}")
    print(f"Images: {len(sample.get('images', []))}")
    print(f"Reviews: {len(sample.get('reviews', []))}")



