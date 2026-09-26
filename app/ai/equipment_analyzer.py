import json
from ollama import chat


def analyze_equipment(device: dict, search_results: list):
    """
    Convert retrieved web documentation into structured
    equipment/component/failure information.
    """

    # Keep the context reasonably small for the local model
    sources = []

    for index, result in enumerate(search_results, start=1):
        title = result.get("title", "")
        title_lower = title.lower()

        # Only send high-value technical documents to the reasoning model
        is_useful_document = (
            "service manual" in title_lower
            or "user's guide" in title_lower
            or "user guide" in title_lower
        )

        if not is_useful_document:
            continue

        content = (
            result.get("extracted_content")
            or result.get("content", "")
        )

        # Service manuals contain the most useful physical-component
        # information, but the relevant sections may not be at the
        # beginning of the document.
        if "service manual" in title_lower:
         # Search throughout the service manual for sections that are
            # likely to contain actual physical parts and disassembly steps.
            keywords = [
                "removing the",
                "remove the",
                "disassembly",
                "disassembling",
                "replacement",
                "keypad board",
                "usb board",
                "power board",
                "main board",
                "interface board",
                "chassis",
                "back cover",
                "panel",
            ]

            content_lower = content.lower()
            candidate_chunks = []

            for keyword in keywords:
                search_start = 0

                while True:
                    position = content_lower.find(
                        keyword,
                        search_start
                    )

                    if position == -1:
                        break

                    start = max(0, position - 300)
                    end = min(len(content), position + 1800)

                    candidate_chunks.append(
                        (
                            position,
                            content[start:end]
                        )
                    )

                    search_start = position + len(keyword)

            # Sort sections according to where they occur in the manual.
            candidate_chunks.sort(key=lambda item: item[0])

            # Remove near-duplicate chunks.
            chunks = []
            used_positions = []

            for position, chunk in candidate_chunks:
                if any(
                    abs(position - old_position) < 800
                    for old_position in used_positions
                ):
                    continue

                used_positions.append(position)
                chunks.append(chunk)

                # Prevent the prompt from becoming huge.
                if len(chunks) >= 8:
                    break

            if chunks:
                selected_content = (
                    "\n\n--- SERVICE MANUAL SECTION ---\n\n"
                ).join(chunks)

                selected_content = selected_content[:12000]

            else:
                selected_content = content[:6000]

        else:
            # User guides are useful mainly for ports,
            # controls and externally visible components.
            selected_content = content[:3500]

        sources.append({
            "source_id": index,
            "title": title,
            "url": result.get("url", ""),
            "content": selected_content
        })

    prompt = f"""
You are analyzing technical equipment using retrieved web documentation.

IDENTIFIED DEVICE:
{json.dumps(device, indent=2)}

RETRIEVED SOURCES:
{json.dumps(sources, indent=2)}

Create a structured technical analysis of the equipment.

COMPONENT RULES:

1. external_components:
   Components physically visible in the image or explicitly described
   by the retrieved documentation.

2. internal_components:
   Internal parts/systems identified from retrieved technical
   documentation.

3. Do NOT use nearby_objects from the vision result as device components.

4. Do NOT invent internal components merely from general knowledge.

5. If an internal component is directly supported by a retrieved source:
   evidence_level = "documented"

6. If documentation only supports it indirectly:
   evidence_level = "inferred"

7. Every documented component must contain at least one source_id.

8. If the exact device model is unknown, do NOT present
   model-specific internal architecture as confirmed.

9. If there is insufficient evidence for internal components,
   return an empty internal_components array and explain why
   in limitations.

10. A physical part being listed in a service manual proves that the
    part exists, but does NOT prove its function, dependencies,
    failure effects, or troubleshooting procedure.

11. Do NOT invent functions for components.
    If the source does not explain a component's function,
    use null.

12. Do NOT invent dependencies merely because two components
    appear near each other in a disassembly procedure.

13. Only include a dependency when the retrieved documentation
    explicitly supports the relationship.
    Otherwise omit it.

14. Only include failure_effects when the retrieved documentation
    explicitly describes what happens when that component fails.
    Do not generate generic "malfunction" effects.

15. Only include troubleshooting actions explicitly supported
    by the retrieved documentation.
    Do not assume that a component should be replaced simply
    because it appears in a service manual.

16. Covers, chassis, brackets, screws, labels, and similar
    mechanical parts are physical components, but do not assign
    them electronic input/output functions unless documented.

17. The model in IDENTIFIED DEVICE is authoritative for this analysis.
    If it is not null, do not state that the exact model is unknown.

18. Never cite a source_id unless that specific source supports
    the claim being made.

19. internal_components must contain ONLY physical hardware parts
    or physical hardware assemblies that are actually part of the device.

20. Do NOT classify documentation sections, specifications, features,
    software, firmware, compatibility information, policies, modes,
    interfaces as concepts, or configuration information as physical
    internal components.

21. Examples that are NOT physical internal components:
    "Operating system compatibility",
    "Monitor specifications",
    "Resolution specifications",
    "Supported video modes",
    "Preset display modes",
    "Electrical specifications",
    "Physical characteristics",
    "Environmental characteristics",
    "Ergonomics",
    "Product features",
    "Plug-and-play capability",
    software applications,
    firmware features,
    documentation headings.

22. Ports and connectors such as HDMI, DisplayPort, USB-A, USB-B,
    and USB-C should normally be classified as external_components,
    not internal_components.

23. Do not return duplicate components. If the same physical component
    appears multiple times in the sources, return it only once.

24. Prefer service-manual physical parts such as boards, panels,
    chassis assemblies, covers, brackets, buttons, connectors,
    cables, power assemblies, and display assemblies.

25. A component name must refer to a physical object that a technician
    could physically locate on or inside the equipment.

26. EQUIPMENT IDENTITY IS IMMUTABLE.
    The manufacturer, model, and device_type from IDENTIFIED DEVICE
    are authoritative.

27. Never change the equipment manufacturer or model based on retrieved
    documentation.

28. If a retrieved document describes a different model than the
    identified model, do NOT use that document as evidence for
    model-specific components.

29. The "equipment" object in the output must copy device_type,
    manufacturer, and model exactly from IDENTIFIED DEVICE.

30. Do not place the same component in both external_components
    and internal_components.

31. Labels, QR codes, serial-number labels, regulatory labels,
    mounting holes, external ports, external buttons, slots,
    and external connectors are NOT internal components.

32. For internal_components, prioritize parts explicitly named in
    service-manual removal, disassembly, or replacement procedures.

33. Do not treat a component as internal merely because it appears
    somewhere in the service manual.

Return ONLY valid JSON in this exact general structure:

{{
  "equipment": {{
    "device_type": "",
    "manufacturer": "",
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

  "failure_effects": [
    {{
      "component": "",
      "failure": "",
      "effect": "",
      "source_ids": []
    }}
  ],

  "troubleshooting": [
    {{
      "problem": "",
      "action": "",
      "source_ids": []
    }}
  ],

  "limitations": []
}}
"""

    response = chat(
        model="qwen2.5vl:7b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "num_ctx": 8192,
            "temperature": 0.1
        }
    )

    content = response["message"]["content"]

    # Remove Markdown fences if Qwen adds them
    content = (
        content
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    analysis = json.loads(content)

    # Equipment identity comes from the image-analysis stage.
    # The reasoning model is not allowed to change it.
    analysis["equipment"] = {
        "device_type": device.get("device_type"),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model")
    }

    # For the MVP, do not expose failure propagation or repair actions
    # unless we later build a dedicated evidence-validation step.
    # This prevents generic LLM assumptions from being presented as
    # manufacturer-documented facts.
    analysis["failure_effects"] = []
    analysis["troubleshooting"] = []

    # Remove contradictory model-identity limitations.
    if device.get("model"):
        analysis["limitations"] = [
            limitation
            for limitation in analysis.get("limitations", [])
            if "exact model" not in limitation.lower()
        ]

    return analysis