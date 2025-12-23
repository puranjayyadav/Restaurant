# Review Enrichment Guide

## How to Add Reviews to Your Scraped Places

### Quick Start

1. **Run your Python scraper** to get places:
```bash
python advanced_grid_scraper.py
# This creates files like: Financial_District,_New_York,_NY_coffee_shop.json
```

2. **Enrich with reviews**:
```bash
python enrich_with_reviews.py input_file.json output_file.json 10
```

### Example Usage

```bash
# Enrich the first 5 places from Financial District coffee shops
python enrich_with_reviews.py \
  "Financial_District,_New_York,_NY_laptop_friendly_coffee_shop_with_wifi_and_outlets.json" \
  "enriched_coffee_shops.json" \
  5
```

### What It Does

1. ✅ Loads your scraped places
2. ✅ Filters to only highly-rated places (4.0+ stars)
3. ✅ For each place, calls the Node.js scraper to get reviews
4. ✅ Adds reviews to the place data
5. ✅ Saves enriched data to output file
6. ✅ Includes 12-second delays between requests (rate limiting)

### Output Format

```json
{
  "name": "Blue Bottle Coffee",
  "avg_rating": 4.5,
  "total_reviews": 150,
  "reviews": [
    {
      "author": "John Doe",
      "rating": 5,
      "text": "Amazing coffee! The baristas are super friendly...",
      "length": 245
    }
  ],
  "review_count": 5
}
```

### Performance

- **Time per place**: ~15-20 seconds
- **5 places**: ~1.5-2 minutes
- **20 places**: ~6-8 minutes
- **100 places**: ~30-40 minutes

### Tips

1. **Start small**: Test with 5-10 places first
2. **Filter by rating**: Only enrich 4.0+ star places
3. **Run overnight**: For large batches (100+ places)
4. **Monitor**: Watch the console output for errors

### Advanced: Batch Processing

Process all your scraped files:

```python
import glob
import subprocess

# Find all scraped JSON files
files = glob.glob("*_New_York_NY_*.json")

for file in files:
    output = file.replace('.json', '_with_reviews.json')
    print(f"Processing {file}...")
    
    subprocess.run([
        'python', 
        'enrich_with_reviews.py', 
        file, 
        output, 
        '10'  # Limit to 10 places per file
    ])
```

### Troubleshooting

**No reviews found?**
- Check if the place name is correct
- Try running `final_scraper.js` manually to test
- Google Maps might have changed their layout

**Script too slow?**
- Reduce `max_reviews_per_place` (default: 5)
- Increase `min_rating` filter (e.g., 4.5)
- Process fewer places at a time

**Rate limited by Google?**
- Increase delay between requests (line 88)
- Use a VPN or proxy
- Process in smaller batches with breaks
