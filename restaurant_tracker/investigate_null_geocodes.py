"""
Investigate articles with null geocoding results.
Fetches lemon8_articles with NULL stops_lat/stops_lng to analyze why geocoding failed.
"""
import os
import json
from typing import Dict, Any, List
from supabase_config import get_supabase_client


def fetch_null_geocode_articles(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch articles where stops_lat or stops_lng is NULL.
    """
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Supabase client not available.")
        return []

    try:
        # Fetch articles with null stops_lat
        result_lat = (
            supabase.table("lemon8_articles")
            .select("url, itinerary_data, enriched_itinerary_data, stops_lat, stops_lng")
            .is_("stops_lat", "null")
            .not_.is_("itinerary_data", "null")
            .limit(limit)
            .execute()
        )
        
        # Fetch articles with null stops_lng
        result_lng = (
            supabase.table("lemon8_articles")
            .select("url, itinerary_data, enriched_itinerary_data, stops_lat, stops_lng")
            .is_("stops_lng", "null")
            .not_.is_("itinerary_data", "null")
            .limit(limit)
            .execute()
        )
        
        # Combine and deduplicate by URL
        all_articles = {}
        for article in (result_lat.data or []) + (result_lng.data or []):
            all_articles[article.get("url")] = article
        
        return list(all_articles.values())
        
    except Exception as exc:
        print(f"ERROR: Failed to fetch articles: {exc}")
        import traceback
        traceback.print_exc()
        return []


def analyze_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze an article to understand why geocoding might have failed.
    """
    url = article.get("url", "")
    itinerary_data = article.get("itinerary_data")
    enriched_data = article.get("enriched_itinerary_data")
    stops_lat = article.get("stops_lat")
    stops_lng = article.get("stops_lng")
    
    analysis = {
        "url": url,
        "url_short": url[-60:] if len(url) > 60 else url,
        "stops_lat_status": "NULL" if stops_lat is None else f"array[{len(stops_lat)}]",
        "stops_lng_status": "NULL" if stops_lng is None else f"array[{len(stops_lng)}]",
        "has_itinerary_data": itinerary_data is not None,
        "has_enriched_data": enriched_data is not None,
        "itinerary_data_type": type(itinerary_data).__name__ if itinerary_data else None,
        "city": None,
        "num_stops": 0,
        "stops": [],
        "issues": [],
    }
    
    # Parse itinerary_data
    data = itinerary_data
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            analysis["issues"].append("itinerary_data is malformed JSON string")
            return analysis
    
    if isinstance(data, list):
        # Check for malformed list-of-keys pattern
        if all(isinstance(item, str) for item in data):
            analysis["issues"].append(f"itinerary_data is list of strings: {data}")
            return analysis
    
    if not isinstance(data, dict):
        analysis["issues"].append(f"itinerary_data is not a dict: {type(data).__name__}")
        return analysis
    
    analysis["city"] = data.get("city")
    if not analysis["city"]:
        analysis["issues"].append("No city field in itinerary_data")
    
    stops = data.get("stops")
    if not isinstance(stops, list):
        analysis["issues"].append(f"stops is not a list: {type(stops).__name__ if stops else 'None'}")
        return analysis
    
    analysis["num_stops"] = len(stops)
    
    if len(stops) == 0:
        analysis["issues"].append("Empty stops array")
        return analysis
    
    for i, stop in enumerate(stops):
        stop_info = {
            "index": i,
            "place_name": stop.get("place_name", ""),
            "search_query": stop.get("search_query", ""),
            "has_lat": stop.get("lat") is not None,
            "has_lng": stop.get("lng") is not None,
            "potential_issues": [],
        }
        
        # Check for issues with place_name
        place_name = stop_info["place_name"]
        if not place_name:
            stop_info["potential_issues"].append("Empty place_name")
        elif len(place_name) < 3:
            stop_info["potential_issues"].append(f"Very short place_name: '{place_name}'")
        
        # Check for problematic characters
        if any(c in place_name for c in ['+', '|', ':']):
            stop_info["potential_issues"].append("Contains special separators (+, |, :)")
        
        # Check for location-only names that might confuse geocoder
        location_terms = ['nyc', 'new york', 'manhattan', 'brooklyn', 'queens', 'bronx', 'harlem', 'soho', 'tribeca']
        lower_name = place_name.lower()
        if any(term in lower_name for term in location_terms) and len(place_name.split()) <= 3:
            stop_info["potential_issues"].append("Name contains only location terms, no business name")
        
        # Check if search_query is missing or same as place_name
        search_query = stop_info["search_query"]
        if not search_query:
            stop_info["potential_issues"].append("Empty search_query")
        elif search_query.lower() == place_name.lower():
            stop_info["potential_issues"].append("search_query identical to place_name (no additional context)")
        
        analysis["stops"].append(stop_info)
    
    return analysis


def print_analysis(analysis: Dict[str, Any]):
    """Pretty print an article analysis."""
    print("=" * 80)
    print(f"URL: {analysis['url_short']}")
    print(f"stops_lat: {analysis['stops_lat_status']}, stops_lng: {analysis['stops_lng_status']}")
    print(f"City: {analysis['city']}")
    print(f"Number of stops: {analysis['num_stops']}")
    
    if analysis["issues"]:
        print(f"\n❌ TOP-LEVEL ISSUES:")
        for issue in analysis["issues"]:
            print(f"   - {issue}")
    
    if analysis["stops"]:
        print(f"\n📍 STOPS:")
        for stop in analysis["stops"]:
            place_name = stop["place_name"][:50] if stop["place_name"] else "(empty)"
            search_query = stop["search_query"][:40] if stop["search_query"] else "(empty)"
            print(f"\n   [{stop['index']}] {place_name}")
            print(f"       search_query: {search_query}")
            if stop["potential_issues"]:
                for issue in stop["potential_issues"]:
                    print(f"       ⚠️  {issue}")
    
    print()


def main():
    print("🔍 Investigating articles with NULL geocoding results...\n")
    
    articles = fetch_null_geocode_articles(limit=30)
    print(f"Found {len(articles)} articles with NULL stops_lat or stops_lng\n")
    
    if not articles:
        print("No articles found with NULL geocoding results.")
        return
    
    # Analyze each article
    analyses = []
    for article in articles:
        analysis = analyze_article(article)
        analyses.append(analysis)
        print_analysis(analysis)
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    total_stops = sum(a["num_stops"] for a in analyses)
    articles_with_issues = [a for a in analyses if a["issues"]]
    empty_stops = [a for a in analyses if a["num_stops"] == 0]
    no_city = [a for a in analyses if not a["city"] and not a["issues"]]
    
    print(f"Total articles analyzed: {len(analyses)}")
    print(f"Total stops across all articles: {total_stops}")
    print(f"Articles with top-level issues: {len(articles_with_issues)}")
    print(f"Articles with empty stops array: {len(empty_stops)}")
    print(f"Articles missing city field: {len(no_city)}")
    
    # Count stop-level issues
    stop_issue_counts = {}
    for analysis in analyses:
        for stop in analysis["stops"]:
            for issue in stop["potential_issues"]:
                stop_issue_counts[issue] = stop_issue_counts.get(issue, 0) + 1
    
    if stop_issue_counts:
        print(f"\n📍 Stop-level issue breakdown:")
        for issue, count in sorted(stop_issue_counts.items(), key=lambda x: -x[1]):
            print(f"   {count:3d} stops: {issue}")
    
    # Save raw data for further analysis
    output_file = "null_geocode_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analyses, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Full analysis saved to: {output_file}")


if __name__ == "__main__":
    main()
