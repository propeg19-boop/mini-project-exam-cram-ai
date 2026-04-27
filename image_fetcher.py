# utils/image_fetcher.py — SerpAPI Google Images Fetcher
# ─────────────────────────────────────────────────────────
# Queries SerpAPI's Google Images endpoint for educational
# diagram images related to a given topic.
#
# Steps:
#   1. Build query: topic + " diagram labeled"
#   2. Call SerpAPI → /search.json with engine=google_images
#   3. Extract "original" URL from each images_results entry
#   4. Filter: must be a valid http/https URL
#   5. Return first 3 valid URLs
#
# Falls back to placeholder images if the API fails or
# returns no results — so the frontend never breaks.

import os
import requests


SERPAPI_URL = "https://serpapi.com/search.json"

# Placeholder images used when SerpAPI returns nothing or errors.
# These are reliable public domain diagram images.
FALLBACK_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Placeholder_view_vector.svg/800px-Placeholder_view_vector.svg.png",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Placeholder_view_vector.svg/800px-Placeholder_view_vector.svg.png",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Placeholder_view_vector.svg/800px-Placeholder_view_vector.svg.png",
]


def is_valid_url(url: str) -> bool:
    """
    Basic check — must start with http:// or https://.
    Filters out data URIs and malformed results.
    """
    return isinstance(url, str) and (url.startswith("http://") or url.startswith("https://"))


def fetch_images(topic: str, count: int = 3) -> dict:
    """
    Main function called by app.py → /get-images route.

    Args:
        topic (str): The subject to search for (e.g. "photosynthesis")
        count (int): Number of images to return (default 3)

    Returns:
        { "images": ["url1", "url2", "url3"] }
    """
    api_key = os.getenv("SERPAPI_KEY")

    # If no key configured, skip API call and use fallbacks
    if not api_key:
        print("[Images] SERPAPI_KEY not set — returning fallback images.")
        return {"images": FALLBACK_IMAGES[:count]}

    # Append "diagram labeled" to get educational visuals
    query = f"{topic} diagram labeled"

    params = {
        "engine":  "google_images",
        "q":       query,
        "api_key": api_key,
        "num":     10,   # Request more than needed to allow filtering
    }

    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=15)
        response.raise_for_status()

        data          = response.json()
        image_results = data.get("images_results", [])

        # Extract and validate the "original" (full-res) URL from each result
        valid_urls = []
        for item in image_results:
            url = item.get("original", "")
            if is_valid_url(url):
                valid_urls.append(url)
            if len(valid_urls) >= count:
                break   # Stop once we have enough

        # If SerpAPI returned results but none had valid URLs
        if not valid_urls:
            print(f"[Images] No valid images found for '{topic}' — using fallbacks.")
            return {"images": FALLBACK_IMAGES[:count]}

        # Pad with fallbacks if fewer than `count` valid images found
        while len(valid_urls) < count:
            valid_urls.append(FALLBACK_IMAGES[len(valid_urls) % len(FALLBACK_IMAGES)])

        return {"images": valid_urls[:count]}

    except requests.exceptions.Timeout:
        print("[Images] SerpAPI timed out — returning fallback images.")
        return {"images": FALLBACK_IMAGES[:count]}

    except requests.exceptions.HTTPError as e:
        print(f"[Images] SerpAPI HTTP error {e.response.status_code} — returning fallbacks.")
        return {"images": FALLBACK_IMAGES[:count]}

    except requests.exceptions.RequestException as e:
        print(f"[Images] SerpAPI request failed: {e} — returning fallbacks.")
        return {"images": FALLBACK_IMAGES[:count]}

    except Exception as e:
        print(f"[Images] Unexpected error: {e} — returning fallbacks.")
        return {"images": FALLBACK_IMAGES[:count]}
