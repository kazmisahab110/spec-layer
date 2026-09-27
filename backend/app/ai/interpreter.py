import json
import os
import re
from pathlib import Path

import ollama
from dotenv import load_dotenv


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

OLLAMA_INTERPRETER_MODEL = os.getenv(
    "OLLAMA_INTERPRETER_MODEL",
    "gpt-oss:20b-cloud",
)


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

VALID_SCOPES = {
    "internal",
    "external",
    "unknown",
}

VALID_RELATIONSHIPS = {
    "contains",
    "connected_to",
    "mounted_on",
    "supplies_power",
    "sends_signal",
    "receives_signal",
    "drives",
    "cools",
    "supports",
    "feeds",
}


# ---------------------------------------------------------
# JSON cleanup
# ---------------------------------------------------------

def _clean_json(text: str) -> str:
    """
    Remove common Markdown wrappers around JSON.
    """

    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    return text.strip()


# ---------------------------------------------------------
# Source preparation
# ---------------------------------------------------------

def _prepare_documents(search_results: list[dict]) -> list[dict]:
    """
    Prepare retrieved documents for GPT-OSS.

    Each usable document receives a stable integer source_id.
    These IDs are later validated by Python before any component
    or relationship is allowed into the final graph.
    """

    documents = []
    used_source_ids = set()

    for index, result in enumerate(search_results[:12], start=1):
        content = (
            result.get("raw_content")
            or result.get("content")
            or ""
        )

        if not isinstance(content, str):
            content = str(content or "")

        content = content.strip()

        if not content:
            continue

        raw_source_id = result.get("source_id")

        try:
            source_id = int(raw_source_id)
        except (TypeError, ValueError):
            source_id = index

        # Protect against duplicate or invalid IDs.
        if source_id <= 0 or source_id in used_source_ids:
            source_id = index

            while source_id in used_source_ids:
                source_id += 1

        used_source_ids.add(source_id)

        documents.append(
            {
                "source_id": source_id,
                "title": str(result.get("title") or "").strip(),
                "url": str(result.get("url") or "").strip(),
                "content": content[:30000],
            }
        )

    return documents


def _format_documents_for_prompt(
    documents: list[dict],
) -> str:
    """
    Give the model explicit source boundaries.

    This is easier for the model to cite reliably than a large
    JSON dump containing all retrieved documents.
    """

    blocks = []

    for document in documents:
        blocks.append(
            "\n".join(
                [
                    f'===== SOURCE {document["source_id"]} =====',
                    f'TITLE: {document["title"]}',
                    f'URL: {document["url"]}',
                    "",
                    "DOCUMENT CONTENT:",
                    document["content"],
                    f'===== END SOURCE {document["source_id"]} =====',
                ]
            )
        )

    return "\n\n".join(blocks)


# ---------------------------------------------------------
# Source validation
# ---------------------------------------------------------

def _normalize_source_ids(
    value,
    valid_source_ids: set[int],
) -> list[int]:
    """
    Normalize citations and reject IDs that do not correspond
    to one of the documents actually supplied to the model.
    """

    if not isinstance(value, list):
        return []

    normalized = []

    for item in value:
        try:
            source_id = int(item)
        except (TypeError, ValueError):
            continue

        if source_id not in valid_source_ids:
            continue

        if source_id not in normalized:
            normalized.append(source_id)

    return normalized


# ---------------------------------------------------------
# Component normalization
# ---------------------------------------------------------

def _normalize_component(
    component: dict,
    valid_source_ids: set[int],
) -> dict | None:
    """
    Normalize one component returned by the model.

    A component is only accepted as documented when at least
    one valid supplied source supports it.
    """

    if not isinstance(component, dict):
        return None

    name = str(
        component.get("name") or ""
    ).strip()

    if not name:
        return None

    source_ids = _normalize_source_ids(
        component.get("source_ids"),
        valid_source_ids,
    )

    # Critical grounding rule:
    # no citation -> no documented component.
    if not source_ids:
        return None

    scope = str(
        component.get("scope") or "unknown"
    ).strip().lower()

    if scope not in VALID_SCOPES:
        scope = "unknown"

    function = component.get("function")

    if function is not None:
        function = str(function).strip() or None

    generic_media_query = str(
        component.get("generic_media_query")
        or name
    ).strip()

    generic_3d_query = str(
        component.get("generic_3d_query")
        or name
    ).strip()

    return {
        "id": "",
        "name": name,
        "scope": scope,
        "function": function,
        "evidence_level": "documented",
        "source_ids": source_ids,
        "generic_media_query": generic_media_query,
        "generic_3d_query": generic_3d_query,
    }


def _slugify_component_id(name: str) -> str:
    """
    Generate a stable frontend-friendly component ID.

    Example:
        Power Board -> power-board
    """

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        name.lower(),
    ).strip("-")

    return slug or "component"


def _assign_unique_component_ids(
    components: list[dict],
) -> None:
    """
    Assign deterministic unique IDs to components.

    These IDs are what graph relationships reference.
    """

    used = {}

    for component in components:
        base = _slugify_component_id(
            component["name"]
        )

        count = used.get(base, 0) + 1
        used[base] = count

        component["id"] = (
            base
            if count == 1
            else f"{base}-{count}"
        )


def _build_name_to_id(
    components: list[dict],
) -> dict[str, str]:
    return {
        component["name"].strip().lower():
            component["id"]
        for component in components
    }


# ---------------------------------------------------------
# Relationship normalization
# ---------------------------------------------------------

def _normalize_relationship(
    relationship: dict,
    name_to_id: dict[str, str],
    valid_source_ids: set[int],
) -> dict | None:
    """
    Normalize one documented relationship.

    The LLM references component names.
    The backend converts those names into stable graph IDs.

    Relationships without valid evidence are rejected.
    """

    if not isinstance(relationship, dict):
        return None

    source_name = str(
        relationship.get("source") or ""
    ).strip()

    target_name = str(
        relationship.get("target") or ""
    ).strip()

    relation_type = str(
        relationship.get("type") or ""
    ).strip().lower()

    if not source_name or not target_name:
        return None

    source_id = name_to_id.get(
        source_name.lower()
    )

    target_id = name_to_id.get(
        target_name.lower()
    )

    # Both endpoints must be accepted documented components.
    if not source_id or not target_id:
        return None

    # No self-relationships.
    if source_id == target_id:
        return None

    if relation_type not in VALID_RELATIONSHIPS:
        return None

    source_ids = _normalize_source_ids(
        relationship.get("source_ids"),
        valid_source_ids,
    )

    # Critical grounding rule:
    # no supporting citation -> no graph edge.
    if not source_ids:
        return None

    return {
        "source": source_id,
        "target": target_id,
        "type": relation_type,
        "evidence_level": "documented",
        "source_ids": source_ids,
    }


def _deduplicate_relationships(
    relationships: list[dict],
) -> list[dict]:
    """
    Deduplicate graph edges.

    If the model returns the same edge multiple times with different
    supporting documents, merge the source IDs instead of discarding
    useful evidence.
    """

    merged = {}

    for relationship in relationships:
        key = (
            relationship["source"],
            relationship["target"],
            relationship["type"],
        )

        if key not in merged:
            merged[key] = relationship.copy()
            merged[key]["source_ids"] = list(
                relationship["source_ids"]
            )
            continue

        existing_ids = merged[key]["source_ids"]

        for source_id in relationship["source_ids"]:
            if source_id not in existing_ids:
                existing_ids.append(source_id)

    return list(merged.values())


# ---------------------------------------------------------
# Limitations
# ---------------------------------------------------------

def _normalize_limitations(value) -> list[str]:
    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


# ---------------------------------------------------------
# Main interpreter
# ---------------------------------------------------------

def interpret_internal_components(
    device: dict,
    search_results: list[dict],
) -> dict:
    """
    Interpret retrieved documentation into a grounded
    equipment/component graph.

    Despite the historical function name, this extracts both
    internal and external documented physical components.

    Every returned documented component and relationship must
    contain at least one valid source_id.
    """

    # Only send product identity to the cloud interpreter.
    # Do not forward visible text or unique identifiers.
    safe_device = {
        "device_type": device.get("device_type"),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
    }

    documents = _prepare_documents(
        search_results
    )

    if not documents:
        return {
            "equipment": safe_device,
            "components": [],
            "internal_components": [],
            "external_components": [],
            "unknown_components": [],
            "relationships": [],
            "limitations": [
                "No usable documentation was available for component extraction."
            ],
        }

    valid_source_ids = {
        int(document["source_id"])
        for document in documents
    }

    documents_text = _format_documents_for_prompt(
        documents
    )

    prompt = f"""
You are analyzing technical documentation for an identified
physical product or piece of equipment.

The product may be any kind of physical equipment, including
vehicles, consumer electronics, computers, keyboards, phones,
cameras, appliances, pumps, motors, power tools, industrial
machinery, instruments, mechanical equipment, electrical equipment,
or electromechanical equipment.

Do NOT assume any particular product category.

==================================================
IDENTIFIED EQUIPMENT
==================================================

{json.dumps(safe_device, indent=2)}

==================================================
RETRIEVED DOCUMENTATION
==================================================

Each supplied document is surrounded by:

===== SOURCE <integer ID> =====

and:

===== END SOURCE <integer ID> =====

The integer ID is the ONLY value that may be placed in source_ids.

{documents_text}

==================================================
PRIMARY TASK
==================================================

Extract PHYSICAL COMPONENTS that the supplied documentation establishes
as belonging to the identified equipment.

A component may be mechanical, electrical, electronic,
electromechanical, hydraulic, pneumatic, structural, optical, thermal,
or another real physical assembly or part.

Do NOT use a predefined component taxonomy.

Do NOT invent components merely because similar products usually
contain them.

Only return components supported by the supplied documentation.

Do NOT use documentation for a different product model as evidence.

If a document concerns a different model, variant, or product and does
not explicitly apply to the identified equipment, do not use it as
evidence.

==================================================
COMPONENT SCOPE
==================================================

Every component MUST receive exactly one scope:

"internal"
    The documentation establishes that the component is located inside
    the main equipment enclosure, body, housing, structure, or assembly.

"external"
    The documentation establishes that the component belongs to the
    equipment and is externally exposed, externally attached,
    user-accessible, or forms part of the outside physical structure.

"unknown"
    The documentation establishes that the component belongs to the
    equipment, but does not provide enough evidence to determine
    internal versus external location.

Scope describes physical location or assembly position.

Do not classify scope merely because a component appears in a service
manual.

Do not guess.

When the documentation establishes component existence but not its
physical scope, use "unknown".

==================================================
FUNCTION
==================================================

Only provide a component's function when the supplied documentation
explicitly explains it.

Otherwise return:

"function": null

Do NOT infer function solely from general engineering knowledge.

==================================================
EVIDENCE AND CITATION RULES
==================================================

Evidence attribution is mandatory.

Every component MUST contain source_ids with at least one valid integer
SOURCE ID.

Example:

"source_ids": [1]

or:

"source_ids": [1, 3]

A documented component with:

"source_ids": []

is INVALID.

For each component:

- Cite only documents that explicitly establish the existence of that
  physical component for the identified equipment.

- Do not cite a source merely because it discusses the overall product.

- Do not cite a source merely because it discusses a similar product.

- Do not invent source IDs.

- Do not use URLs, titles, or strings such as "SOURCE 1" in source_ids.

- source_ids must contain integer IDs only.

- If no supplied document supports a component, OMIT that component.

The value:

"evidence_level": "documented"

means that at least one supplied document directly supports the claim.

==================================================
RELATIONSHIPS
==================================================

After extracting supported components, extract explicitly documented
physical or functional relationships BETWEEN those components.

Allowed relationship types are ONLY:

"contains"
"connected_to"
"mounted_on"
"supplies_power"
"sends_signal"
"receives_signal"
"drives"
"cools"
"supports"
"feeds"

Meanings:

contains
    The source component physically contains the target component.

connected_to
    Documentation explicitly establishes a physical, electrical, or
    mechanical connection.

mounted_on
    The source component is explicitly documented as physically mounted
    on the target component.

supplies_power
    The source component is explicitly documented as supplying
    electrical power to the target component.

sends_signal
    Documentation explicitly establishes signal flow from source to
    target.

receives_signal
    Documentation explicitly establishes that the source receives a
    signal from the target.

drives
    Documentation explicitly establishes that the source mechanically
    or electrically drives the target.

cools
    Documentation explicitly establishes that the source cools the
    target.

supports
    Documentation explicitly establishes that the source physically
    supports the target.

feeds
    Documentation explicitly establishes that the source feeds
    documented material, fluid, or media into the target.

CRITICAL RELATIONSHIP RULES:

- Do NOT create relationships from common engineering knowledge.

- The fact that two components both exist is NOT evidence that they are
  connected.

- A document mentioning both components independently is NOT sufficient
  evidence for a relationship.

- The supplied documentation itself must establish the relationship.

- If the relationship is not explicitly supported, return NO EDGE.

- source and target MUST exactly match component names from the
  components array.

- Every relationship MUST contain at least one valid source_id that
  supports that exact relationship.

A relationship with:

"source_ids": []

is INVALID and must not be returned.

==================================================
GENERIC MEDIA QUERY
==================================================

For every component create:

"generic_media_query"

This is a short search phrase for a GENERIC reference image of the
physical component.

Use approximately 2 to 6 words where practical.

Remove:
- manufacturer names
- model numbers
- serial numbers
- marketing names

Preserve useful technical terminology required to identify the
physical object.

Do not change the component into a different physical object merely to
obtain better search results.

==================================================
GENERIC 3D QUERY
==================================================

For every component create:

"generic_3d_query"

This query will be sent to a generic 3D-model search engine.

The goal is a generic physical representation of the documented
component, NOT an exact manufacturer-specific replacement part.

Preserve enough physical detail to distinguish the component from other
objects of the same broad class.

Generic means not tied to this exact manufacturer or model.

Generic does NOT mean removing useful technical terminology.

Remove manufacturer/model identifiers while preserving documented
physical/interface terminology.

Do NOT invent connector types, dimensions, materials, construction,
geometry, electrical standards, mounting styles, or subtypes that are
not supported by the documentation.

If there is insufficient information for a more specific generic query,
preserve the documented component terminology.

==================================================
SAFETY / GROUNDING
==================================================

Do NOT provide:
- repair procedures
- replacement procedures
- disassembly instructions
- failure predictions
- safety-critical advice
- invented dependencies

This task is ONLY:

1. identify documented physical components
2. classify their documented physical scope
3. identify explicitly documented relationships
4. generate generic media-search terminology
5. cite the supplied documentation supporting each factual claim

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

Do not include Markdown or explanatory text.

Use exactly this structure:

{{
  "equipment": {{
    "device_type": null,
    "manufacturer": null,
    "model": null
  }},
  "components": [
    {{
      "name": "Example component",
      "scope": "internal",
      "function": null,
      "evidence_level": "documented",
      "source_ids": [1],
      "generic_media_query": "generic component",
      "generic_3d_query": "generic component"
    }}
  ],
  "relationships": [
    {{
      "source": "Exact component name",
      "target": "Exact component name",
      "type": "connected_to",
      "evidence_level": "documented",
      "source_ids": [1]
    }}
  ],
  "limitations": []
}}

IMPORTANT:

The [1] values above are FORMAT EXAMPLES only.

Use the actual SOURCE IDs from the supplied documentation.

Never return a documented component or relationship with an empty
source_ids array.

If no supported components exist:

"components": []

If no explicitly documented relationships exist:

"relationships": []

Do NOT manufacture claims merely to populate either array.
"""

    # -----------------------------------------------------
    # GPT-OSS
    # -----------------------------------------------------

    response = ollama.chat(
        model=OLLAMA_INTERPRETER_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={
            "temperature": 0,
        },
    )

    raw_text = (
        response.get("message", {})
        .get("content", "")
    )

    if not raw_text.strip():
        raise RuntimeError(
            "GPT-OSS returned an empty interpreter response."
        )

    cleaned = _clean_json(
        raw_text
    )

    try:
        result = json.loads(
            cleaned
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GPT-OSS returned invalid JSON."
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "GPT-OSS interpreter response was not a JSON object."
        )

    # -----------------------------------------------------
    # Equipment identity
    #
    # Never allow the cloud interpreter to alter the identity
    # established by the vision stage.
    # -----------------------------------------------------

    result["equipment"] = safe_device

    # -----------------------------------------------------
    # Components
    #
    # Python performs the final grounding check.
    # The LLM cannot create a "documented" component unless
    # it cites at least one source that actually exists.
    # -----------------------------------------------------

    raw_components = result.get(
        "components",
        [],
    )

    components = []

    rejected_component_count = 0

    if isinstance(raw_components, list):
        for raw_component in raw_components:
            component = _normalize_component(
                raw_component,
                valid_source_ids,
            )

            if component is None:
                rejected_component_count += 1
                continue

            components.append(
                component
            )

    _assign_unique_component_ids(
        components
    )

    # -----------------------------------------------------
    # Split components by physical scope
    # -----------------------------------------------------

    internal_components = [
        component
        for component in components
        if component["scope"] == "internal"
    ]

    external_components = [
        component
        for component in components
        if component["scope"] == "external"
    ]

    unknown_components = [
        component
        for component in components
        if component["scope"] == "unknown"
    ]

    # -----------------------------------------------------
    # Relationships
    #
    # Only relationships between accepted documented
    # components can survive normalization.
    # -----------------------------------------------------

    name_to_id = _build_name_to_id(
        components
    )

    raw_relationships = result.get(
        "relationships",
        [],
    )

    relationships = []

    rejected_relationship_count = 0

    if isinstance(raw_relationships, list):
        for raw_relationship in raw_relationships:
            relationship = _normalize_relationship(
                raw_relationship,
                name_to_id,
                valid_source_ids,
            )

            if relationship is None:
                rejected_relationship_count += 1
                continue

            relationships.append(
                relationship
            )

    relationships = _deduplicate_relationships(
        relationships
    )

    # -----------------------------------------------------
    # Limitations
    # -----------------------------------------------------

    limitations = _normalize_limitations(
        result.get(
            "limitations",
            [],
        )
    )

    # These messages are useful during development and also
    # explain why an LLM-returned claim may not appear in the
    # final API response.
    if rejected_component_count:
        limitations.append(
            f"{rejected_component_count} component claim(s) were "
            "removed because they lacked valid supporting source IDs "
            "or were structurally invalid."
        )

    if rejected_relationship_count:
        limitations.append(
            f"{rejected_relationship_count} relationship claim(s) "
            "were removed because they lacked valid supporting source "
            "IDs, referenced unavailable components, or were "
            "structurally invalid."
        )

    # -----------------------------------------------------
    # Final normalized contract
    # -----------------------------------------------------

    return {
        "equipment": safe_device,
        "components": components,
        "internal_components": internal_components,
        "external_components": external_components,
        "unknown_components": unknown_components,
        "relationships": relationships,
        "limitations": limitations,
    }