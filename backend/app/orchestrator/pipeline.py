import json

from app.ai.qwen_vision import analyze_image
from search.tavily import search_equipment
from app.ai.interpreter import interpret_internal_components
from app.media.pexels import add_component_images
from app.media.sketchfab import add_component_models


def run_pipeline(image_path: str) -> dict:
    print("\n[1] Identifying product with Qwen Vision...\n")
    device = analyze_image(image_path)
    print(json.dumps(device, indent=2))

    print("\n[2] Retrieving product documentation with Tavily...\n")
    results = search_equipment(device)

    print("\n[3] Extracting documented components and relationships with GPT-OSS...\n")
    analysis = interpret_internal_components(
        device=device,
        search_results=results,
    )

    print("\n[4] Finding generic component images with Pexels...\n")
    analysis = add_component_images(
        analysis=analysis,
        device=device,
    )

    print("\n[5] Finding generic component 3D references with Sketchfab...\n")
    analysis = add_component_models(
        analysis=analysis,
        device=device,
    )

    # ---------------------------------------------------------
    # Rebuild scope-specific component views
    # ---------------------------------------------------------
    #
    # Media enrichment happens against analysis["components"].
    # Rebuild these lists afterwards so every scope-specific view
    # contains the final enriched component objects.
    #
    # This also gives the frontend a stable API contract:
    #
    #   analysis["components"]             -> all graph nodes
    #   analysis["internal_components"]    -> internal nodes
    #   analysis["external_components"]    -> external nodes
    #   analysis["unknown_components"]     -> unclassified nodes
    #   analysis["relationships"]          -> graph edges
    #
    # No equipment-specific component rules are used here.
    # ---------------------------------------------------------

    components = analysis.get("components", [])

    analysis["internal_components"] = [
        component
        for component in components
        if component.get("scope") == "internal"
    ]

    analysis["external_components"] = [
        component
        for component in components
        if component.get("scope") == "external"
    ]

    analysis["unknown_components"] = [
        component
        for component in components
        if component.get("scope") == "unknown"
    ]

    print(
        "\n[6] Finalized component graph "
        f"({len(components)} components, "
        f"{len(analysis.get('relationships', []))} relationships)...\n"
    )

    return {
        "device": device,
        "search_results": results,
        "analysis": analysis,
    }


if __name__ == "__main__":
    image_path = input("Enter image path: ").strip().strip('"')
    print(json.dumps(run_pipeline(image_path), indent=2))