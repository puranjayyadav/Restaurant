import os
import time
import requests


def get_unsplash_image(query: str, access_key: str, output_folder: str = "ai_covers") -> str | None:
    """
    Fetch a portrait/vertical aesthetic photo from Unsplash API.
    Returns the image URL and downloads it locally.
    """
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": f"{query} aesthetic",
        "orientation": "portrait",
        "per_page": 5,
        "order_by": "relevant",
    }
    headers = {"Authorization": f"Client-ID {access_key}"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"[WARN] Unsplash HTTP {resp.status_code} for '{query}': {resp.text[:200]}")
            return None
        data = resp.json()
        results = data.get("results", [])
        if not results:
            print(f"[WARN] No results for '{query}'")
            return None
        img = results[0]
        img_url = img.get("urls", {}).get("regular")
        if not img_url:
            print(f"[WARN] No image URL in result for '{query}'")
            return None

        os.makedirs(output_folder, exist_ok=True)
        img_resp = requests.get(img_url, timeout=30)
        if img_resp.status_code == 200:
            filename = f"{output_folder}/{query.replace(' ', '_').lower()}.jpg"
            with open(filename, "wb") as f:
                f.write(img_resp.content)
            print(f"[OK] {query} -> {filename}")
        else:
            print(f"[WARN] Failed to download image (HTTP {img_resp.status_code}) for '{query}'")

        return img_url
    except Exception as e:
        print(f"[ERROR] {query}: {e}")
        return None


if __name__ == "__main__":
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        raise SystemExit("Set UNSPLASH_ACCESS_KEY environment variable.")

    samples = [
        "SoHo Date Night",
        "Hidden Speakeasy Circuit",
        "West Village Coffee Run",
        "Brooklyn Vintage Crawl",
        "Rainy Day Museums",
    ]
    for q in samples:
        get_unsplash_image(q, access_key=access_key)
        time.sleep(0.5)