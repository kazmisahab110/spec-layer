import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(env_path)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    raise ValueError("PEXELS_API_KEY was not found in .env")

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


def make_generic_query(component_name: str, device: dict | None = None) -> str:
    """
    Last-resort fallback only. The interpreter should normally provide
    generic_media_query dynamically.
    """
    query = str(component_name or "").strip()

    if device:
        for value in (device.get("manufacturer"), device.get("model")):
            if value:
                query = re.sub(
                    re.escape(str(value)),
                    "",
                    query,
                    flags=re.IGNORECASE,
                )

    return " ".join(query.split())


def search_component_image(query: str) -> dict | None:
    query = str(query or "").strip()
    if not query:
        return None

    try:
        response = requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1},
            timeout=10,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])

        if not photos:
            return None

        photo = photos[0]
        src = photo.get("src", {})
        image_url = src.get("large") or src.get("large2x") or src.get("original")
        thumbnail_url = src.get("medium") or src.get("small") or image_url

        if not image_url:
            return None

        return {
            "type": "generic_reference",
            "source": "Pexels",
            "query": query,
            "url": image_url,
            "thumbnail_url": thumbnail_url,
            "photographer": photo.get("photographer"),
            "photographer_url": photo.get("photographer_url"),
            "pexels_url": photo.get("url"),
            "alt": photo.get("alt"),
        }

    except (requests.RequestException, ValueError, TypeError) as error:
        print(f'Pexels search failed for "{query}": {error}', flush=True)
        return None


def add_component_images(analysis: dict, device: dict | None = None) -> dict:
    components = analysis.get(
    "components",
    analysis.get("internal_components", []),
    )
    if not isinstance(components, list):
        return analysis

    print("\nSearching Pexels for generic component images...\n", flush=True)
    cache = {}

    for component in components:
        if not isinstance(component, dict):
            continue

        name = component.get("name")
        if not name:
            continue

        query = component.get("generic_media_query")
        if not query:
            query = make_generic_query(name, device)

        query = str(query or "").strip()

        image = cache.get(query) if query in cache else search_component_image(query)
        cache[query] = image

        media = component.get("media")
        if not isinstance(media, dict):
            media = {}

        media["image_url"] = image.get("url") if image else None
        media["thumbnail_url"] = image.get("thumbnail_url") if image else None
        media["image"] = image
        media.setdefault("model_3d", None)

        component["media"] = media

    return analysis
