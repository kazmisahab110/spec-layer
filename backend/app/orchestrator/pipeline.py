import json

from app.ai.qwen_vision import analyze_image
from search.tavily import search_equipment
from app.ai.interpreter import interpret_internal_components


def run_pipeline(image_path: str):

    # STEP 1 — Vision
    print("\n[1] Analyzing image with Qwen...\n")

    device = analyze_image(image_path)

    print("\n=== DEVICE IDENTIFICATION ===\n")
    print(json.dumps(device, indent=2))


    # STEP 2 — Documentation retrieval
    print("\n[2] Searching documentation with Tavily...\n")

    results = search_equipment(device)

    print("\n=== SEARCH RESULTS ===\n")

    for result in results:
        print("TITLE:", result.get("title"))
        print("URL:", result.get("url"))

        content = result.get("content", "")
        print("CONTENT:", content[:400])

        print("-" * 70)


    # STEP 3 — Gemini interprets the documentation
    print("\n[3] Interpreting documentation with Gemini...\n")

    analysis = interpret_internal_components(
        device=device,
        search_results=results
    )

    print("\n=== GEMINI INTERPRETATION ===\n")
    print(json.dumps(analysis, indent=2))


    return {
        "device": device,
        "search_results": results,
        "analysis": analysis
    }


if __name__ == "__main__":
    image_path = input("Enter image path: ").strip().strip('"')
    run_pipeline(image_path)