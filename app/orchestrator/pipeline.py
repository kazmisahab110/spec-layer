import json

from app.ai.qwen_vision import analyze_image
from app.search.tavily import search_equipment
from app.ai.equipment_analyzer import analyze_equipment


def run_pipeline(image_path: str):

    # STEP 1 — Identify equipment from image
    print("\n[1] Analyzing image with Qwen...\n")

    device = analyze_image(image_path)

    print("\n=== DEVICE IDENTIFICATION ===\n")
    print(json.dumps(device, indent=2))


    # STEP 2 — Search web for documentation
    print("\n[2] Searching documentation with Tavily...\n")

    results = search_equipment(device)

    print("\n=== SEARCH RESULTS ===\n")

    for result in results:
        print("TITLE:", result["title"])
        print("URL:", result["url"])
        print("CONTENT:", result["content"][:400])
        print("-" * 70)


    # STEP 3 — Analyze documentation with Qwen
    print("\n[3] Building equipment knowledge with Qwen...\n")

    analysis = analyze_equipment(device, results)

    print("\n=== EQUIPMENT ANALYSIS ===\n")
    print(json.dumps(analysis, indent=2))


    # Return everything for our future FastAPI endpoint
    return {
        "device": device,
        "search_results": results,
        "analysis": analysis
    }


if __name__ == "__main__":

    image_path = input("Enter image path: ").strip().strip('"')

    run_pipeline(image_path)