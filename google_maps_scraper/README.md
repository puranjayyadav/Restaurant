# Google Maps Scraper Suite

A comprehensive toolkit for scraping Google Maps data including places and reviews.

## 📁 Directory Structure

```
google_maps_scraper/
├── advanced_grid_scraper.py      # Main Python scraper (grid-based search)
├── standalone_scraper.py          # Simple single-location scraper
├── enrich_with_reviews.py         # Add reviews to scraped places
├── analyze_results.py             # Analyze scraped data
├── REVIEW_ENRICHMENT_GUIDE.md     # How to add reviews
└── review_scraper_test/           # Node.js Puppeteer review scraper
    ├── final_scraper.js           # ⭐ Working review scraper
    ├── review_scraper.js          # Module version
    ├── search_scraper.js          # Alternative implementation
    └── README.md                  # Review scraper documentation
```

## 🚀 Quick Start

### 1. Scrape Places (Python)

```bash
cd google_maps_scraper
python advanced_grid_scraper.py
```

This will scrape places for all neighborhoods and vibes defined in the script.

### 2. Add Reviews (Python + Node.js)

```bash
python enrich_with_reviews.py input.json output.json 10
```

This calls the Node.js scraper to add reviews to your places.

### 3. Analyze Results

```bash
python analyze_results.py output.json
```

## 📊 What Each Script Does

### `advanced_grid_scraper.py` ⭐ Main Scraper
- Grid-based search across neighborhoods
- Batched processing with rate limiting
- Extracts: name, address, rating, hours, photos
- Output: JSON files per neighborhood/vibe

### `enrich_with_reviews.py` ⭐ Review Enrichment
- Adds Google Maps reviews to scraped places
- Filters by rating (4.0+ stars)
- Calls Node.js Puppeteer scraper
- Includes rate limiting (12s between requests)

### `review_scraper_test/final_scraper.js` ⭐ Review Scraper
- Puppeteer-based browser automation
- Clicks "More" buttons to expand reviews
- Extracts full review text
- Works with exact Google Maps selectors

### `analyze_results.py`
- Statistics on scraped data
- Top categories and tags
- Average ratings
- Photo coverage

## 🔧 Setup

### Python Requirements
```bash
pip install requests
```

### Node.js Requirements
```bash
cd review_scraper_test
npm install puppeteer
```

## 📖 Usage Examples

### Scrape Coffee Shops in SoHo
Edit `advanced_grid_scraper.py` to include only SoHo, then:
```bash
python advanced_grid_scraper.py
```

### Get Reviews for Top 5 Places
```bash
python enrich_with_reviews.py \
  "SoHo,_New_York,_NY_coffee_shop.json" \
  "soho_with_reviews.json" \
  5
```

### Test Review Scraper Directly
```bash
cd review_scraper_test
node final_scraper.js "Blue Bottle Coffee NYC" 5
```

## ⚠️ Important Notes

### Rate Limiting
- Python scraper: 5-12 second delays between searches
- Review scraper: 12 second delays between places
- **Don't scrape too fast or Google will block you!**

### Performance
- **Places scraping**: ~2-3 seconds per grid point
- **Review scraping**: ~15-20 seconds per place
- **100 places with reviews**: ~30-40 minutes

### Best Practices
1. Start with small batches (5-10 places)
2. Only fetch reviews for highly-rated places (4.0+)
3. Run large batches overnight
4. Monitor console output for errors

## 🐛 Troubleshooting

### No places found?
- Check if Google Maps changed their response structure
- Try reducing grid size
- Verify location name is correct

### No reviews found?
- Google Maps selectors may have changed
- Run with `headless: false` to debug
- Check `review_scraper_test/README.md`

### Rate limited?
- Increase delays between requests
- Use a VPN or proxy
- Process in smaller batches

## 📚 Documentation

- **Review Enrichment**: See `REVIEW_ENRICHMENT_GUIDE.md`
- **Review Scraper**: See `review_scraper_test/README.md`

## 🎯 Workflow

```
1. Run advanced_grid_scraper.py
   ↓
2. Get JSON files with places
   ↓
3. Run enrich_with_reviews.py
   ↓
4. Get enriched JSON with reviews
   ↓
5. Run analyze_results.py
   ↓
6. See statistics and insights
```

---

**Last Updated**: 2025-12-23  
**Status**: ✅ Production Ready  
**Review Scraper**: ✅ Working with exact selectors
