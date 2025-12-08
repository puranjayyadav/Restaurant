"""Extract structured itinerary data from Lemon8 article content using free LLM service"""
import os
import sys
import time
import json
import re
import requests
from typing import Dict, List, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required if using environment variables directly

# Input and output files
INPUT_FILE = "lemon8_article_links.json"
OUTPUT_FILE = "lemon8_article_links.json"

# API Keys - MUST be set via environment variable (OPENROUTER_API_KEY)
# Never hardcode API keys in source code!
OPENROUTER_API_KEY = None  # Removed hardcoded key for security

# LLM Service Configuration
EXTRACTION_PROMPT = """You are a precision Data Extraction Agent. Your job is to convert raw HTML content from social media posts into structured JSON itineraries.

RULES:

1. INPUT: You will receive raw HTML content from a Lemon8 post.

2. TARGET: Extract every location/restaurant mentioned.

3. PRIORITY: Look for text inside <a class="l8editor-poi"> tags — these are the official Place Names. If not present, infer names from the text (e.g., "1. Katz's Deli").

4. CONTEXT: Extract specific recommendations (what to order, vibe, tips) from the surrounding <p> tags.

5. SEARCH QUERY: You MUST generate a 'search_query' field for each stop. Format: "{Place Name} {Neighborhood} {City}". If City is unknown, default to "New York".

6. OUTPUT: Return ONLY valid JSON. Do not include markdown formatting (```json), explanations, or conversational filler.

JSON SCHEMA:

{
  "itinerary_title": "String (Infer from <h1> or content)",
  "city": "String (e.g., New York, Brooklyn)",
  "stops": [
    {
      "place_name": "String (Official name)",
      "search_query": "String (Optimized for Google Maps)",
      "category": "String (e.g., Food, Activity, Coffee, Nightlife)",
      "notes": "String (Summary of what the creator said about this spot)"
    }
  ]
}"""

def extract_with_openrouter(html_content: str, api_key: Optional[str] = None, log_func=None) -> Optional[str]:
    """Extract itinerary data using OpenRouter free tier."""
    if log_func is None:
        log_func = print
    
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            log_func("  ⚠ OpenRouter: No API key found in environment variables")
            log_func("  ⚠ Set OPENROUTER_API_KEY in your .env file or environment")
            return None
    
    # Truncate HTML content if too large (OpenRouter has token limits)
    max_html_length = 10000  # Limit HTML to ~10k chars
    if len(html_content) > max_html_length:
        html_content = html_content[:max_html_length] + "... [truncated]"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Lemon8 Itinerary Extractor"
    }
    
    # Try different free models - verified free models from OpenRouter
    # Models are ordered by reliability (confirmed working first, then by size/capability)
    # The script automatically skips 404 (not found) errors and tries the next model
    models_to_try = [
        "meta-llama/llama-3.2-3b-instruct:free",  # Confirmed working (may be rate limited)
        "mistralai/mistral-7b-instruct:free",  # Confirmed exists (may be rate limited, often returns empty)
        # Verified free models from OpenRouter API
        "tngtech/deepseek-r1t2-chimera:free",
        "kwaipilot/kat-coder-pro:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "tngtech/deepseek-r1t-chimera:free",
        "z-ai/glm-4.5-air:free",
        "tngtech/tng-r1t-chimera:free",
        "amazon/nova-2-lite-v1:free",
        "qwen/qwen3-coder:free",
        "google/gemma-3-27b-it:free",
        "openai/gpt-oss-20b:free",
    ]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Extract itinerary data from this HTML content:\n\n{html_content}"}
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        try:
            # Use data=json.dumps() as per official documentation
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )
            
            log_func(f"  OpenRouter response status ({model}): {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    
                    if "message" in choice:
                        message = choice["message"]
                        
                        # Get content - might be None or empty
                        content = message.get("content")
                        if content:
                            content = content.strip()
                            if content:
                                log_func(f"  ✓ OpenRouter returned {len(content)} characters using {model}")
                                return content
                            else:
                                log_func(f"  ⚠ {model}: Content is empty string, trying next...")
                        else:
                            log_func(f"  ⚠ {model}: Content field is None or missing, trying next...")
                    else:
                        log_func(f"  ⚠ {model}: No 'message' field in choice, trying next...")
                else:
                    log_func(f"  ⚠ {model}: Unexpected response format, trying next...")
                continue  # Try next model
            elif response.status_code == 402:
                log_func(f"  ⚠ Model {model} requires payment, trying next...")
                continue  # Try next model
            elif response.status_code == 429:
                log_func(f"  ⚠ Model {model} rate limited (429), waiting 5 seconds and trying next...")
                time.sleep(5)  # Wait before trying next model
                continue  # Try next model
            else:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_text = json.dumps(error_json, indent=2)
                except:
                    pass
                log_func(f"  ⚠ OpenRouter API error ({model}): {response.status_code}")
                log_func(f"  Error: {error_text[:500]}")
                continue  # Try next model
        except Exception as e:
            log_func(f"  ⚠ OpenRouter API exception ({model}): {e}")
            import traceback
            log_func(f"  Traceback: {traceback.format_exc()[:500]}")
            continue  # Try next model
    
    # If all models failed
    log_func(f"  ⚠ All OpenRouter models failed")
    return None
    

def extract_with_huggingface(html_content: str) -> Optional[str]:
    """Extract itinerary data using Hugging Face Inference API (free, no key required)."""
    # HuggingFace deprecated the old endpoint, skip for now
    print(f"  ⚠ HuggingFace: Old endpoint deprecated, skipping")
    return None

def parse_json_response(response_text: str) -> Optional[Dict]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    if not response_text:
        return None
    
    # Remove markdown code blocks if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    # Try to find JSON object in the response
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(0)
    
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parsing error: {e}")
        print(f"  Response preview: {response_text[:200]}...")
        return None

def extract_itinerary_data(html_content: str, log_func=None) -> Optional[Dict]:
    """Extract itinerary data from HTML content using available LLM service."""
    if log_func is None:
        log_func = print
    
    if not html_content:
        return None
    
    log_func("  Calling LLM service...")
    
    # Try OpenRouter first (free tier)
    log_func("  Trying OpenRouter...")
    result = extract_with_openrouter(html_content, log_func=log_func)
    if result:
        parsed = parse_json_response(result)
        if parsed:
            log_func("  ✓ Successfully extracted with OpenRouter")
            return parsed
        else:
            log_func("  ⚠ OpenRouter returned data but couldn't parse JSON")
    else:
        log_func("  ⚠ OpenRouter failed or returned no data")
    
    # Try HuggingFace as last resort
    log_func("  Trying HuggingFace...")
    result = extract_with_huggingface(html_content)
    if result:
        parsed = parse_json_response(result)
        if parsed:
            log_func("  ✓ Successfully extracted with HuggingFace")
            return parsed
        else:
            log_func("  ⚠ HuggingFace returned data but couldn't parse JSON")
    else:
        log_func("  ⚠ HuggingFace failed or returned no data")
    
    log_func("  ✗ All LLM services failed")
    return None

def load_articles():
    """Load articles from JSON file."""
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found!")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

def save_articles(articles):
    """Save articles to JSON file."""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return False

def main():
    """Main extraction function."""
    # Also log to file for debugging
    log_file = "extraction_log.txt"
    log_f = open(log_file, 'w', encoding='utf-8')
    
    def log_print(msg):
        print(msg)
        log_f.write(msg + "\n")
        log_f.flush()
    
    # Load articles
    articles = load_articles()
    total_articles = len(articles)
    
    log_print(f"Loaded {total_articles} articles from {INPUT_FILE}")
    log_print(f"Starting to extract itinerary data...")
    log_print(f"Output will be saved to: {OUTPUT_FILE}")
    log_print(f"{'='*60}")
    
    # Check for API keys
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if not openrouter_key:
        log_print("\n✗ ERROR: OPENROUTER_API_KEY not found in environment variables")
        log_print("  Please set it in your .env file or as an environment variable")
        log_print("  Make sure your .env file exists and contains: OPENROUTER_API_KEY=sk-or-v1-...")
        log_f.close()
        sys.exit(1)
    
    log_print("\n✓ OpenRouter API key configured")
    log_print("Ready to extract itinerary data!\n")
    
    extracted_count = 0
    skipped_count = 0
    error_count = 0
    already_extracted = 0
    
    for idx, article in enumerate(articles, 1):
        url = article.get("url", "")
        content = article.get("content")
        
        if not content:
            log_print(f"\n[{idx}/{total_articles}] Skipping (no content): {url}")
            skipped_count += 1
            continue
        
        # Check if already extracted
        if "itinerary_data" in article and article["itinerary_data"]:
            log_print(f"\n[{idx}/{total_articles}] Already extracted: {url}")
            already_extracted += 1
            continue
        
        log_print(f"\n[{idx}/{total_articles}] Extracting itinerary from article...")
        log_print(f"  URL: {url}")
        
        # Extract itinerary data
        itinerary_data = extract_itinerary_data(content, log_func=log_print)
        
        # Update article with extracted data
        if itinerary_data:
            article["itinerary_data"] = itinerary_data
            article["extracted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            extracted_count += 1
            log_print(f"  ✓ Extracted {len(itinerary_data.get('stops', []))} stops")
        else:
            article["itinerary_data"] = None
            article["extraction_error"] = "Failed to extract itinerary data"
            article["extracted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            error_count += 1
        
        # Save after each extraction
        if save_articles(articles):
            log_print(f"  ✓ JSON file updated")
        else:
            log_print(f"  ⚠ Warning: Failed to save JSON file")
        
        # Rate limiting - longer delay to avoid rate limits
        time.sleep(5)
    
    log_print(f"\n{'='*60}")
    log_print(f"Extraction completed!")
    log_print(f"  Total articles: {total_articles}")
    log_print(f"  Successfully extracted: {extracted_count}")
    log_print(f"  Already had data: {already_extracted}")
    log_print(f"  Errors: {error_count}")
    log_print(f"  Skipped (no content): {skipped_count}")
    log_print(f"\nResults saved to: {OUTPUT_FILE}")
    log_f.close()

if __name__ == "__main__":
    main()
