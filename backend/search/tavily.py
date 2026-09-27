import os
import re
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

api_key = os.getenv("TAVILY_API_KEY")
if not api_key:
    raise ValueError("TAVILY_API_KEY was not found in .env")

client = TavilyClient(api_key=api_key)


def _identity_text(device: dict) -> str:
    values = [
        device.get("manufacturer"),
        device.get("model"),
        device.get("device_type"),
    ]
    return " ".join(str(v).strip() for v in values if v).strip()


def _contains_model_token(text: str, model: str) -> bool:
    if not text or not model:
        return False
    pattern = rf"(?<![A-Za-z0-9]){re.escape(model)}(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def search_equipment(device: dict) -> list:
    """
    Retrieve documentation for any identified physical product.
    Queries are built from product identity, not product category rules.
    """
    identity = _identity_text(device)
    model = device.get("model")

    if not identity:
        return []

    document_queries = [
        "service manual PDF",
        "repair manual PDF",
        "maintenance manual PDF",
        "parts catalog PDF",
        "parts manual PDF",
        "workshop manual PDF",
        "disassembly PDF",
        "technical manual PDF",
        "user manual PDF",
    ]

    queries = [f"{identity} {suffix}" for suffix in document_queries]

    all_results = []
    seen_urls = set()

    for query in queries:
        print(f"\nSearching Tavily for: {query}\n")

        try:
            response = client.search(query=query, max_results=4)
        except Exception as error:
            print(f"Search failed: {error}")
            continue

        for result in response.get("results", []):
            url = result.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_results.append(result)

    def document_score(result: dict) -> int:
        title = (result.get("title") or "").lower()
        url = (result.get("url") or "").lower()
        score = 0

        weights = {
            "service manual": 100,
            "repair manual": 95,
            "workshop manual": 95,
            "maintenance manual": 90,
            "parts catalog": 90,
            "parts manual": 90,
            "technical manual": 80,
            "disassembly": 80,
            "service": 35,
            "repair": 35,
            "parts": 30,
            "manual": 20,
            "user guide": 15,
            "user manual": 15,
        }

        for phrase, weight in weights.items():
            if phrase in title:
                score += weight

        if ".pdf" in url:
            score += 20

        if model and _contains_model_token(title, str(model)):
            score += 40

        manufacturer = device.get("manufacturer")
        if manufacturer and str(manufacturer).lower() in title:
            score += 15

        return score

    all_results.sort(key=document_score, reverse=True)
    all_results = all_results[:12]

    print("\nExtracting documentation content...\n")

    for result in all_results:
        url = result.get("url", "")
        title = result.get("title", "")

        try:
            extracted = client.extract(urls=[url])
            extracted_results = extracted.get("results", [])
            if not extracted_results:
                continue

            raw_content = extracted_results[0].get("raw_content", "")
            if raw_content:
                result["extracted_content"] = raw_content[:30000]
                print(f"Extracted {len(raw_content)} characters from: {title}")
        except Exception as error:
            print(f"Could not extract: {title}")
            print(f"Reason: {error}")

    return all_results
