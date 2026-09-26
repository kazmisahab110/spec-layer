import json
import os
from pathlib import Path

from app.ai.qwen_vision import analyze_image
from app.search.tavily import search_equipment
from app.ai.interpreter import interpret_internal_components


def print_header(title: str):
    print("\n")
    print("=" * 80)
    print(title)
    print("=" * 80)
    print()


def run_full_ai_test(image_path: str):
    """
    Full AI workflow test:

    IMAGE
      ↓
    Qwen Vision
      ↓
    Structured device JSON
      ↓
    Tavily
      ↓
    Search results + extracted manual/PDF content
      ↓
    Interpreter
      ↓
    Structured internal-component JSON
    """

    image = Path(image_path)

    if not image.exists():
        raise FileNotFoundError(
            f"Image does not exist: {image_path}"
        )

    # ============================================================
    # STAGE 1 — QWEN VISION
    # ============================================================

    print_header("STAGE 1 — QWEN VISION")

    print(f"Analyzing image:\n{image}\n")

    device = analyze_image(str(image))

    print("Qwen structured JSON:\n")
    print(json.dumps(device, indent=2))

    # Basic validation
    if not isinstance(device, dict):
        raise ValueError(
            "Qwen did not return a JSON object."
        )

    print("\n✓ Qwen vision stage completed successfully.")

    # ============================================================
    # STAGE 2 — TAVILY DOCUMENT RETRIEVAL
    # ============================================================

    print_header("STAGE 2 — TAVILY DOCUMENT RETRIEVAL")

    print(
        "Searching for service manuals, repair manuals, "
        "maintenance documentation, parts information, "
        "and user guides...\n"
    )

    search_results = search_equipment(device)

    if not search_results:
        raise ValueError(
            "Tavily returned no search results."
        )

    print(
        f"\nTavily returned {len(search_results)} results.\n"
    )

    # ============================================================
    # PRINT SAFE SUMMARY OF TAVILY RESULTS
    # ============================================================

    tavily_summary = []

    for index, result in enumerate(
        search_results,
        start=1
    ):
        title = result.get("title", "Unknown title")
        url = result.get("url", "")
        search_content = result.get("content", "")
        extracted_content = result.get(
            "extracted_content",
            ""
        )

        item = {
            "source_id": index,
            "title": title,
            "url": url,
            "search_snippet_characters": len(
                search_content
            ),
            "extracted_document_characters": len(
                extracted_content
            ),
            "has_extracted_document": bool(
                extracted_content
            )
        }

        tavily_summary.append(item)

        print("-" * 80)
        print(f"SOURCE ID: {index}")
        print(f"TITLE: {title}")
        print(f"URL: {url}")

        if extracted_content:
            print(
                "EXTRACTED DOCUMENT: YES "
                f"({len(extracted_content):,} characters)"
            )
        else:
            print("EXTRACTED DOCUMENT: NO")

        if search_content:
            preview = (
                search_content[:300]
                .replace("\n", " ")
                .strip()
            )

            print(f"SEARCH PREVIEW: {preview}")

    print("\n✓ Tavily retrieval stage completed successfully.")

    # ============================================================
    # STAGE 3 — DOCUMENT INTERPRETER
    # ============================================================

    print_header("STAGE 3 — DOCUMENT INTERPRETER")

    print(
        "Sending retrieved technical documentation "
        "to interpreter...\n"
    )

    interpreted = interpret_internal_components(
        device,
        search_results
    )

    if not isinstance(interpreted, dict):
        raise ValueError(
            "Interpreter did not return a JSON object."
        )

    print("\nInterpreter structured JSON:\n")

    print(
        json.dumps(
            interpreted,
            indent=2
        )
    )

    print(
        "\n✓ Documentation interpreter "
        "completed successfully."
    )

    # ============================================================
    # FINAL RESULT
    # ============================================================

    print_header("FINAL AI WORKFLOW RESULT")

    final_result = {
        "device_identification": {
            "device_type": device.get(
                "device_type"
            ),
            "manufacturer": device.get(
                "manufacturer"
            ),
            "model": device.get(
                "model"
            ),
            "uncertainties": device.get(
                "uncertainties",
                []
            )
        },

        "document_sources": tavily_summary,

        "equipment_interpretation": interpreted
    }

    print(
        json.dumps(
            final_result,
            indent=2
        )
    )

    print_header("WORKFLOW COMPLETE")

    print("✓ Qwen Vision")
    print("✓ Structured device identification")
    print("✓ Tavily search")
    print("✓ Manual/document extraction")
    print("✓ Document interpreter")
    print("✓ Structured component output")

    return final_result


if __name__ == "__main__":

    print_header("FIELDLENS — FULL AI PIPELINE TEST")

    image_path = input(
        "Enter equipment image path: "
    )

    # Allows dragging a file into PowerShell,
    # which often surrounds the path with quotes.
    image_path = image_path.strip().strip('"').strip("'")

    try:
        run_full_ai_test(image_path)

    except KeyboardInterrupt:
        print("\n\nTest cancelled.")

    except Exception as error:
        print_header("WORKFLOW FAILED")

        print(
            f"{type(error).__name__}: {error}"
        )

        raise