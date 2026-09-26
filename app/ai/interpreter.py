import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# Load project-root .env
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)


def interpret_internal_components(
    device: dict,
    search_results: list
):
    """
    Read Tavily-retrieved technical documents and identify
    documented physical internal components.

    This stage is intentionally independent of Qwen.
    """

    documents = []

    for index, result in enumerate(search_results, start=1):
        title = result.get("title", "")
        title_lower = title.lower()

        # Prefer documentation likely to expose internal hardware.
        is_technical_document = (
            "service manual" in title_lower
            or "repair manual" in title_lower
            or "maintenance manual" in title_lower
            or "teardown" in title_lower
            or "disassembly" in title_lower
            or "parts manual" in title_lower
            or "user's guide" in title_lower
            or "user guide" in title_lower
        )

        if not is_technical_document:
            continue

        content = (
            result.get("extracted_content")
            or result.get("content", "")
        )

        if not content:
            continue

        documents.append({
            "source_id": index,
            "title": title,
            "url": result.get("url", ""),
            "content": content
        })

        # Prevent irrelevant search results from bloating the request.
        if len(documents) >= 5:
            break

    prompt = f"""
You are a technical equipment documentation interpreter.

Your job is to read the supplied technical documentation and identify
the physical INTERNAL components of the identified equipment.

IDENTIFIED EQUIPMENT:

{json.dumps(device, indent=2)}

DOCUMENTATION:

{json.dumps(documents, indent=2)}

STRICT RULES:

1. Only identify components supported by the supplied documentation.

2. Focus on physical INTERNAL hardware components and assemblies.

3. Search service manuals, repair manuals, teardown/disassembly
   procedures, maintenance manuals, parts manuals, and user manuals.

4. Examples of valid internal components include physical objects such as:
   - main boards
   - power boards
   - interface boards
   - controller boards
   - keypad boards
   - PCBs
   - power-supply assemblies
   - internal cables
   - internal connectors
   - chassis assemblies
   - display panel assemblies
   - backlight assemblies

   These are examples only. Do NOT assume the identified equipment
   contains them.

5. Do NOT include:
   - HDMI ports
   - DisplayPort ports
   - external USB ports
   - external buttons
   - stands
   - VESA mounting holes
   - QR codes
   - serial numbers
   - service tags
   - regulatory labels
   - documentation headings
   - specifications
   - software
   - firmware
   - features
   - operating modes

6. A component must refer to a physical object a technician could
   physically locate inside the equipment.

7. Do not invent components from general knowledge.

8. Do not invent functions.

9. If the documentation explicitly explains the function, include it.
   Otherwise set function to null.

10. Every component must contain source_ids identifying the documents
    that support its existence.

11. Do not return duplicate components.

12. Prefer evidence from service, repair, teardown, disassembly,
    maintenance, and parts documentation over ordinary user guides.

13. The IDENTIFIED EQUIPMENT identity is authoritative.

14. Never change its manufacturer, device type, or model.

15. If a document describes a different model, do NOT use its
    model-specific architecture as evidence.

16. Do NOT infer failure effects or repair instructions.
    This interpreter is ONLY identifying internal physical components.

Return ONLY valid JSON using this structure:

{{
    "equipment": {{
        "device_type": "",
        "manufacturer": "",
        "model": null
    }},

    "internal_components": [
        {{
            "name": "",
            "function": null,
            "evidence_level": "documented",
            "source_ids": []
        }}
    ],

    "limitations": []
}}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    content = response.text.strip()

    # Remove markdown fences if returned.
    content = (
        content
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    analysis = json.loads(content)

    # Never allow the interpreter to modify equipment identity.
    analysis["equipment"] = {
        "device_type": device.get("device_type"),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model")
    }

    return analysis

if __name__ == "__main__":
    test_device = {
        "device_type": "Flat Panel Monitor",
        "manufacturer": "DELL",
        "model": "P2726H"
    }

    test_search_results = [
        {
            "title": "Dell Pro P 27 Monitor P2726H Simplified Service Manual",
            "url": "https://example.com/service-manual.pdf",
            "extracted_content": """
            Removing the Main Board

            Disconnect all cables from the main board.
            Remove the screws securing the main board to the chassis.
            Remove the main board.

            Removing the Power Board

            Disconnect the power board cable.
            Remove the screws securing the power board.
            Remove the power board from the chassis.
            """
        }
    ]

    result = interpret_internal_components(
        test_device,
        test_search_results
    )

    print("\n=== INTERPRETER RESULT ===\n")
    print(json.dumps(result, indent=2))