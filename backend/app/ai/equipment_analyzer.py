import json
from ollama import chat

ANALYSIS_MODEL = "qwen2.5vl:7b"


def analyze_equipment(device: dict, search_results: list) -> dict:
    """
    Optional documentation-analysis stage for arbitrary physical products.

    Unlike the old implementation, this does not search manuals using a
    hardcoded electronics/monitor component vocabulary.
    """
    safe_device = {
        "device_type": device.get("device_type"),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "device_components": device.get("device_components", []),
    }

    sources = []
    for index, result in enumerate(search_results, start=1):
        content = result.get("extracted_content") or result.get("content", "")
        if not content:
            continue

        sources.append({
            "source_id": index,
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": content[:12000],
        })

        if len(sources) >= 5:
            break

    prompt = f"""
Analyze documentation for an arbitrary physical product or piece of equipment.

IDENTIFIED PRODUCT:
{json.dumps(safe_device, indent=2)}

SOURCES:
{json.dumps(sources, indent=2)}

RULES:
- Work for any product category. Do not assume electronics or monitors.
- Components must be physical parts or assemblies supported by the sources.
- Visible components from the image may be external components.
- Never use nearby unrelated objects as components.
- Do not invent hidden parts from general knowledge.
- Functions, dependencies, and relationships require explicit source support.
- Do not invent failure effects or troubleshooting.
- Do not treat specifications, software, firmware, features, operating modes,
  compatibility information, labels, identifiers, or headings as components.
- Preserve the identified manufacturer/model/device type exactly.
- If a source concerns another model, do not use its model-specific
  architecture as evidence.
- A component can be mechanical, electrical, electronic, hydraulic,
  pneumatic, optical, structural, thermal, or another physical type.
- Do not rely on a predefined list of component names.

Return ONLY valid JSON:
{{
  "equipment": {{
    "device_type": null,
    "manufacturer": null,
    "model": null
  }},
  "external_components": [
    {{
      "name": "",
      "function": null,
      "source_ids": []
    }}
  ],
  "internal_components": [
    {{
      "name": "",
      "function": null,
      "evidence_level": "documented",
      "source_ids": []
    }}
  ],
  "dependencies": [
    {{
      "from": "",
      "to": "",
      "relationship": "",
      "evidence_level": "documented",
      "source_ids": []
    }}
  ],
  "failure_effects": [],
  "troubleshooting": [],
  "limitations": []
}}
"""

    response = chat(
        model=ANALYSIS_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"num_ctx": 8192, "temperature": 0.1},
    )

    content = response["message"]["content"]
    content = content.replace("```json", "").replace("```", "").strip()
    analysis = json.loads(content)

    analysis["equipment"] = {
        "device_type": device.get("device_type"),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
    }

    analysis["failure_effects"] = []
    analysis["troubleshooting"] = []

    return analysis
