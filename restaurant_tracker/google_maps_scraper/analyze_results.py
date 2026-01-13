import json
from collections import Counter
import sys

def analyze(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total = len(data)
        print(f"File: {file_path}")
        print(f"Total Places Found: {total}")
        
        # Tags analysis
        all_tags = []
        for p in data:
            tags = p.get('tags')
            if isinstance(tags, list):
                all_tags.extend(tags)
        
        tag_counts = Counter(all_tags).most_common(10)
        print("\nTop 10 Categories/Tags:")
        for tag, count in tag_counts:
            print(f"- {tag}: {count}")
            
        # Rating analysis
        ratings = [p.get('avg_rating') for p in data if p.get('avg_rating') is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            print(f"\nAverage Rating: {avg_rating:.2f}")
            print(f"Max Rating: {max(ratings)}")
            print(f"Min Rating: {min(ratings)}")
        
        # Review counts
        reviews = [p.get('total_reviews') for p in data if p.get('total_reviews') is not None]
        if reviews:
            avg_reviews = sum(reviews) / len(reviews)
            print(f"\nAverage Review Count: {avg_reviews:.0f}")
            print(f"Max Reviews: {max(reviews)}")
            
        # Sample of top-rated places
        print("\nTop Rated Places (by rating and review count):")
        top_places = sorted(data, key=lambda x: (float(x.get('avg_rating') or 0), int(x.get('total_reviews') or 0)), reverse=True)[:5]
        for i, p in enumerate(top_places, 1):
            print(f"{i}. {p.get('name')} - {p.get('avg_rating')} stars ({p.get('total_reviews')} reviews)")
            print(f"   Address: {p.get('full_address')}")
            
        # Check for photos
        places_with_photos = sum(1 for p in data if p.get('photos') and len(p.get('photos')) > 0)
        print(f"\nPlaces with photos: {places_with_photos} / {total}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else 'new_york_city_coffee_shop.json'
    analyze(target)
