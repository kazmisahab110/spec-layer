import base64
import json
import os
import re
from io import BytesIO
from pathlib import Path

import ollama
from dotenv import load_dotenv
from PIL import Image, ImageOps


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

VISION_MODEL = os.getenv(
    "OLLAMA_VISION_MODEL",
    "gemma4:31b-cloud",
)

# Keep enough resolution for product labels and small model text.
MAX_IMAGE_DIMENSION = 1600

JPEG_QUALITY = 85


# ---------------------------------------------------------
# Ollama client
# ---------------------------------------------------------

client = ollama.Client(
    host=OLLAMA_BASE_URL,
    timeout=120,
)


# ---------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------

VISION_SCHEMA = {
    "type": "object",
    "properties": {
        "device_type": {
            "type": ["string", "null"],
        },
        "manufacturer": {
            "type": ["string", "null"],
        },
        "model": {
            "type": ["string", "null"],
        },
        "visible_text": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "device_components": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "nearby_objects": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "uncertainties": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "device_type",
        "manufacturer",
        "model",
        "visible_text",
        "device_components",
        "nearby_objects",
        "uncertainties",
    ],
    "additionalProperties": False,
}


# ---------------------------------------------------------
# Image preprocessing
# ---------------------------------------------------------

def _prepare_image(image_path: str) -> bytes:
    """
    Prepare an image for cloud vision inference.

    The original uploaded image is never modified.

    The longest image dimension is limited to 1600 pixels.
    This retains useful product-label detail without sending
    unnecessarily large phone/camera images.
    """

    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)

        # JPEG does not support transparency.
        if image.mode not in ("RGB", "L"):
            if "A" in image.getbands():
                background = Image.new(
                    "RGB",
                    image.size,
                    "white",
                )

                background.paste(
                    image,
                    mask=image.getchannel("A"),
                )

                image = background

            else:
                image = image.convert("RGB")

        if image.mode != "RGB":
            image = image.convert("RGB")

        width, height = image.size

        largest_dimension = max(
            width,
            height,
        )

        if largest_dimension > MAX_IMAGE_DIMENSION:
            scale = (
                MAX_IMAGE_DIMENSION
                / largest_dimension
            )

            new_width = max(
                1,
                int(width * scale),
            )

            new_height = max(
                1,
                int(height * scale),
            )

            image = image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS,
            )

        buffer = BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
        )

        return buffer.getvalue()


# ---------------------------------------------------------
# Privacy filtering
# ---------------------------------------------------------

PRIVATE_TEXT_PATTERNS = [
    re.compile(
        r"\b(?:s/?n|serial(?:\s+number)?)\s*[:#]?\s*",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bservice\s*tag\s*[:#]?\s*",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bexpress\s*(?:svc|service)\s*(?:code)?\s*[:#]?\s*",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bimei\s*[:#]?\s*",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bvin\s*[:#]?\s*",
        re.IGNORECASE,
    ),

    re.compile(
        r"\basset\s*tag\s*[:#]?\s*",
        re.IGNORECASE,
    ),
]


def _contains_private_identifier(
    text: str,
) -> bool:
    """
    Detect labels associated with unique/private identifiers.
    """

    if not text:
        return False

    return any(
        pattern.search(text)
        for pattern in PRIVATE_TEXT_PATTERNS
    )


def _sanitize_visible_text(
    values,
) -> list[str]:
    """
    Remove unique identifiers from model-produced visible text.

    Product names and model numbers are retained because they
    are needed for documentation retrieval.
    """

    if not isinstance(values, list):
        return []

    cleaned = []

    for value in values:
        text = str(value).strip()

        if not text:
            continue

        if _contains_private_identifier(text):
            continue

        if text not in cleaned:
            cleaned.append(text)

    return cleaned


# ---------------------------------------------------------
# General normalization
# ---------------------------------------------------------

def _normalize_string_or_none(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def _normalize_string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []

    result = []

    for item in value:
        item = str(item).strip()

        if item and item not in result:
            result.append(item)

    return result


# ---------------------------------------------------------
# Robust JSON parsing
# ---------------------------------------------------------

def _extract_json_object(text: str) -> dict:
    """
    Parse a JSON object from the model response.

    Structured output should normally return raw JSON, but this
    parser also tolerates Markdown fences or small amounts of
    surrounding explanatory text.
    """

    if not isinstance(text, str):
        raise RuntimeError(
            "Vision model returned a non-text response."
        )

    text = text.strip()

    if not text:
        raise RuntimeError(
            "Vision model returned an empty response."
        )

    # First attempt: ideal structured-output response.
    try:
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # Second attempt: remove Markdown code fences.
    cleaned = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```\s*$",
        "",
        cleaned,
    ).strip()

    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # Final fallback:
    # find the first complete JSON object in the response.
    decoder = json.JSONDecoder()

    for match in re.finditer(r"\{", cleaned):
        start = match.start()

        try:
            parsed, _ = decoder.raw_decode(
                cleaned[start:]
            )
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    raise RuntimeError(
        "Vision model returned invalid JSON."
    )


# ---------------------------------------------------------
# Vision result validation
# ---------------------------------------------------------

def _normalize_vision_result(
    result: dict,
) -> dict:
    """
    Convert model output into the stable backend contract.
    """

    if not isinstance(result, dict):
        raise RuntimeError(
            "Vision model did not return a JSON object."
        )

    return {
        "device_type": _normalize_string_or_none(
            result.get("device_type")
        ),

        "manufacturer": _normalize_string_or_none(
            result.get("manufacturer")
        ),

        "model": _normalize_string_or_none(
            result.get("model")
        ),

        "visible_text": _sanitize_visible_text(
            result.get("visible_text")
        ),

        "device_components": _normalize_string_list(
            result.get("device_components")
        ),

        "nearby_objects": _normalize_string_list(
            result.get("nearby_objects")
        ),

        "uncertainties": _normalize_string_list(
            result.get("uncertainties")
        ),
    }


# ---------------------------------------------------------
# Vision analysis
# ---------------------------------------------------------

def analyze_image(image_path: str) -> dict:
    """
    Identify the primary physical product/equipment shown in an
    image.

    This stage performs visual equipment identification only.

    Detailed component discovery happens later from retrieved
    technical documentation.
    """

    image_bytes = _prepare_image(
        image_path
    )

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    prompt = """
Analyze the supplied image and identify the PRIMARY physical product
or piece of equipment.

The image may contain ANY kind of physical equipment. Do not assume a
product category before inspecting the image.

Your task is visual PRODUCT IDENTIFICATION only.

Determine:

1. device_type
2. manufacturer
3. model
4. useful non-private visible product-identifying text
5. clearly visible physical components belonging to the product
6. nearby objects that are not part of the product
7. uncertainties

IDENTIFICATION RULES:

- Base manufacturer on explicit visible evidence such as a readable
  manufacturer name, logo, or product label.

- Base the exact model on explicitly readable evidence.

- Do NOT infer an exact model merely from visual appearance.

- If an exact model identifier cannot be read confidently, return null.

- If the manufacturer is not supported by visible evidence, return null.

- Prefer a model identifier explicitly printed on a product label.

- Do not confuse a serial number, service tag, asset tag, barcode,
  regulatory number, manufacturing code, or other unique identifier
  with the product model.

VISIBLE TEXT PRIVACY RULE:

Do NOT return:

- serial numbers
- service tags
- asset tags
- IMEI numbers
- VIN numbers
- license plate numbers
- Express Service Codes
- personally identifying information
- other unique device identifiers

You MAY return non-unique information useful for product
identification, including:

- manufacturer
- product family
- model number
- voltage rating
- generic regulatory text
- non-unique technical labels

DEVICE COMPONENTS:

Only include physical parts that are CLEARLY VISIBLE in the image and
clearly belong to the primary product.

Do NOT infer hidden or internal components.

Do NOT invent components because similar equipment normally contains
them.

Technical documentation will be used in a later pipeline stage to
discover internal components.

UNCERTAINTIES:

Use the uncertainties array only for meaningful uncertainty about the
visual identification.

Do not speculate about dates, product history, authenticity, or other
facts that are not required for identification.

OUTPUT:

Return exactly one JSON object matching the requested structured
schema.

Do not include Markdown.

Do not include code fences.

Do not include commentary before or after the JSON.
"""

    try:
        response = client.chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [
                        image_base64,
                    ],
                }
            ],

            # Ask Ollama for schema-constrained output.
            format=VISION_SCHEMA,

            options={
                "temperature": 0,

                # Enough room for identification without encouraging
                # an unnecessarily long response.
                "num_predict": 600,
            },
        )

    except Exception as exc:
        raise RuntimeError(
            f"Vision analysis failed: {exc}"
        ) from exc

    message = response.get(
        "message",
        {},
    )

    raw_content = message.get(
        "content",
        "",
    )

    try:
        result = _extract_json_object(
            raw_content
        )

    except RuntimeError as exc:
        # Do not expose the complete model response because it could
        # contain text read from a product label.
        raise RuntimeError(
            "Vision model returned invalid JSON."
        ) from exc

    normalized = _normalize_vision_result(
        result
    )

    return normalized