import os
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient


env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise ValueError("TAVILY_API_KEY was not found in .env")

client = TavilyClient(api_key=api_key)


def search_equipment(device: dict):
    manufacturer = device.get("manufacturer") or ""
    model = device.get("model")
    device_type = device.get("device_type") or ""

    all_results = []
    seen_urls = set()

    # ---------------------------------------------------------
    # 1. Build queries.
    #    Service/repair/parts documentation gets highest priority.
    # ---------------------------------------------------------

    if model:
        queries = [
            f"{manufacturer} {model} service manual PDF",
            f"{manufacturer} {model} repair manual PDF",
            f"{manufacturer} {model} disassembly manual PDF",
            f"{manufacturer} {model} parts manual components PDF",
            f"{manufacturer} {model} maintenance manual PDF",
            f"{manufacturer} {model} user guide PDF",
        ]
    else:
        queries = [
            f"{manufacturer} {device_type} service manual PDF",
            f"{manufacturer} {device_type} repair manual PDF",
            f"{manufacturer} {device_type} parts components manual PDF",
            f"{manufacturer} {device_type} user guide PDF",
        ]

    # ---------------------------------------------------------
    # 2. Search each query.
    # ---------------------------------------------------------

    for query in queries:
        print(f"\nSearching Tavily for: {query}\n")

        try:
            response = client.search(
                query=query,
                max_results=4
            )
        except Exception as error:
            print(f"Search failed: {error}")
            continue

        for result in response.get("results", []):
            url = result.get("url", "")
            title = result.get("title", "")

            if not url or url in seen_urls:
                continue

            # Reject obvious near-match model documents.
            # Example:
            # requested: P2726H
            # reject:    P2726HE
            if model:
                model_upper = model.upper()
                title_upper = title.upper()

                if model_upper in title_upper:
                    model_position = title_upper.find(model_upper)
                    after_model = model_position + len(model_upper)

                    if (
                        after_model < len(title_upper)
                        and title_upper[after_model].isalnum()
                    ):
                        print(f"Skipping different model: {title}")
                        continue

            seen_urls.add(url)
            all_results.append(result)

    # ---------------------------------------------------------
    # 3. Score results.
    #    Technical/service documentation should rise to the top.
    # ---------------------------------------------------------

    def document_score(result):
        title = result.get("title", "").lower()
        url = result.get("url", "").lower()

        score = 0

        if "service manual" in title:
            score += 100

        if "repair manual" in title:
            score += 90

        if "disassembly" in title:
            score += 80

        if "maintenance manual" in title:
            score += 75

        if "parts manual" in title:
            score += 70

        if "service" in title:
            score += 40

        if "repair" in title:
            score += 40

        if "user's guide" in title or "user guide" in title:
            score += 30

        if "manual" in title:
            score += 20

        if "parts" in title:
            score += 20

        if "component" in title:
            score += 15

        if ".pdf" in url:
            score += 20

        # Prefer exact-model results
        if model and model.lower() in title:
            score += 30

        return score

    all_results.sort(
        key=document_score,
        reverse=True
    )

    # Keep only the best results
    all_results = all_results[:10]

    # ---------------------------------------------------------
    # 4. Extract useful technical documents.
    # ---------------------------------------------------------

    print("\nExtracting documentation content...\n")

    for result in all_results:
        title = result.get("title", "")
        title_lower = title.lower()
        url = result.get("url", "")

        looks_useful = (
            "service" in title_lower
            or "repair" in title_lower
            or "manual" in title_lower
            or "guide" in title_lower
            or "disassembly" in title_lower
            or "maintenance" in title_lower
            or "parts" in title_lower
            or url.lower().endswith(".pdf")
            or ".pdf?" in url.lower()
        )

        if not looks_useful:
            continue

        try:
            extracted = client.extract(urls=[url])
            extracted_results = extracted.get("results", [])

            if extracted_results:
                raw_content = extracted_results[0].get(
                    "raw_content",
                    ""
                )

                if raw_content:
                    # Keep enough text for later filtering.
                    # equipment_analyzer.py will send a smaller
                    # subset to Qwen.
                    result["extracted_content"] = raw_content[:20000]

                    print(
                        f"Extracted {len(raw_content)} characters "
                        f"from: {title}"
                    )

        except Exception as error:
            print(f"Could not extract: {title}")
            print(f"Reason: {error}")

    return all_results