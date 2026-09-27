import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(env_path)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

if not PEXELS_API_KEY:
    raise ValueError("PEXELS_API_KEY was not found in .env")

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


# ============================================================
# SEARCH CONFIGURATION
# ============================================================

PEXELS_RESULTS_PER_QUERY = 12

# We deliberately prefer "no image" over a misleading image.
MIN_RELEVANCE_SCORE = 0.58


# Words that provide almost no useful semantic information.
STOP_WORDS = {
    "a",
    "an",
    "and",
    "the",
    "of",
    "for",
    "with",
    "to",
    "in",
    "on",
    "from",
    "generic",
    "reference",
    "component",
    "part",
    "parts",
    "device",
    "equipment",
    "hardware",
    "photo",
    "image",
}


# These words are meaningful, but too broad to establish
# component relevance by themselves.
WEAK_COMPONENT_WORDS = {
    "back",
    "front",
    "main",
    "middle",
    "cover",
    "stand",
    "panel",
    "board",
    "cable",
    "port",
    "connector",
    "bracket",
    "mount",
    "mounting",
    "kit",
    "frame",
    "chassis",
    "interface",
    "assembly",
    "module",
    "housing",
    "case",
    "base",
    "support",
    "slot",
}


# Stronger technical terms. A match on one of these is much more
# meaningful than a match on a generic word such as "bracket".
TECHNICAL_TERMS = {
    "usb",
    "hdmi",
    "displayport",
    "display",
    "vesa",
    "lvds",
    "lcd",
    "led",
    "ethernet",
    "rj45",
    "vga",
    "dvi",
    "pcie",
    "sata",
    "nvme",
    "m2",
    "heatsink",
    "motherboard",
    "keypad",
    "backlight",
    "kensington",
    "speaker",
    "webcam",
    "microphone",
    "antenna",
    "battery",
    "fan",
    "keyboard",
    "touchpad",
}


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value: str | None) -> str:
    value = str(value or "").lower()

    # Preserve letters, numbers, spaces, ampersands and hyphens.
    value = re.sub(
        r"[^a-z0-9&\-\s]",
        " ",
        value,
    )

    value = value.replace("-", " ")

    return " ".join(value.split())


def tokenize(value: str | None) -> set[str]:
    normalized = normalize_text(value)

    return {
        token
        for token in normalized.split()
        if len(token) >= 2
        and token not in STOP_WORDS
    }


def strong_tokens(value: str | None) -> set[str]:
    """
    Return tokens that are useful for determining whether a candidate
    really describes the component.

    Generic terms such as "cover", "stand", and "bracket" are excluded.
    """
    return {
        token
        for token in tokenize(value)
        if token not in WEAK_COMPONENT_WORDS
    }


# ============================================================
# DEVICE CONTEXT
# ============================================================

def get_device_context(device: dict | None) -> str:
    """
    Return generic device-category context.

    Example:
        Flat Panel Monitor -> flat panel monitor

    Manufacturer/model are intentionally not used because Pexels
    supplies generic visual references, not exact replacement parts.
    """

    if not isinstance(device, dict):
        return ""

    device_type = str(
        device.get("device_type") or ""
    ).strip()

    return normalize_text(device_type)


def get_device_anchor_tokens(device: dict | None) -> set[str]:
    """
    Produce useful category anchors.

    For example:
        "Flat Panel Monitor"
        -> {"flat", "panel", "monitor"}

    These are used as supporting evidence, not as sufficient evidence
    on their own.
    """
    return tokenize(get_device_context(device))


# ============================================================
# QUERY BUILDING
# ============================================================

def make_generic_query(
    component_name: str,
    device: dict | None = None,
) -> str:
    """
    Build a product-aware generic query.

    Exact manufacturer/model names are removed.
    """

    component_name = str(
        component_name or ""
    ).strip()

    if not component_name:
        return ""

    query = component_name

    if isinstance(device, dict):
        for value in (
            device.get("manufacturer"),
            device.get("model"),
        ):
            if value:
                query = re.sub(
                    re.escape(str(value)),
                    "",
                    query,
                    flags=re.IGNORECASE,
                )

    query = " ".join(query.split())

    device_context = get_device_context(device)

    if device_context:
        query_tokens = tokenize(query)
        context_tokens = tokenize(device_context)

        if not context_tokens.issubset(query_tokens):
            query = f"{device_context} {query}"

    return " ".join(query.split())


def build_search_queries(
    component: dict,
    device: dict | None,
) -> list[str]:
    """
    Build conservative Pexels queries.

    Important:
    We intentionally do NOT fall back to a broad uncontextualized query
    when device context exists. Broad queries were responsible for many
    unrelated results.
    """

    queries: list[str] = []

    component_name = str(
        component.get("name") or ""
    ).strip()

    interpreter_query = str(
        component.get("generic_media_query") or ""
    ).strip()

    device_context = get_device_context(device)

    # --------------------------------------------------------
    # 1. Interpreter query + device context
    # --------------------------------------------------------

    if interpreter_query:
        contextual_query = interpreter_query

        if device_context:
            query_tokens = tokenize(interpreter_query)
            context_tokens = tokenize(device_context)

            if not context_tokens.issubset(query_tokens):
                contextual_query = (
                    f"{device_context} {interpreter_query}"
                )

        queries.append(contextual_query)

    # --------------------------------------------------------
    # 2. Documented component name + device context
    # --------------------------------------------------------

    fallback_query = make_generic_query(
        component_name,
        device,
    )

    if fallback_query:
        queries.append(fallback_query)

    # --------------------------------------------------------
    # 3. Only use an uncontextualized query if we have no
    #    device category at all.
    # --------------------------------------------------------

    if interpreter_query and not device_context:
        queries.append(interpreter_query)

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique_queries: list[str] = []
    seen: set[str] = set()

    for query in queries:
        normalized = normalize_text(query)

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        unique_queries.append(query)

    return unique_queries


# ============================================================
# RELEVANCE SCORING
# ============================================================

def score_photo(
    photo: dict,
    component_name: str,
    query: str,
    device: dict | None = None,
) -> float:
    """
    Conservative metadata relevance score.

    IMPORTANT:
    This does not analyze image pixels.

    It only evaluates Pexels' textual metadata. Therefore the system
    should reject uncertain candidates instead of pretending that a
    weak textual match proves visual relevance.
    """

    alt = str(photo.get("alt") or "")
    pexels_url = str(photo.get("url") or "")

    candidate_text = f"{alt} {pexels_url}"

    candidate_tokens = tokenize(candidate_text)
    component_tokens = tokenize(component_name)
    component_strong = strong_tokens(component_name)

    query_tokens = tokenize(query)
    query_strong = strong_tokens(query)

    device_tokens = get_device_anchor_tokens(device)

    if not candidate_tokens:
        return 0.0

    # --------------------------------------------------------
    # Component coverage
    # --------------------------------------------------------

    component_coverage = 0.0

    if component_tokens:
        component_coverage = (
            len(component_tokens & candidate_tokens)
            / len(component_tokens)
        )

    # --------------------------------------------------------
    # Query coverage
    # --------------------------------------------------------

    query_coverage = 0.0

    if query_tokens:
        query_coverage = (
            len(query_tokens & candidate_tokens)
            / len(query_tokens)
        )

    # --------------------------------------------------------
    # Strong semantic component match
    # --------------------------------------------------------

    strong_component_match = bool(
        component_strong & candidate_tokens
    )

    strong_query_match = bool(
        query_strong & candidate_tokens
    )

    # --------------------------------------------------------
    # Recognized technical terminology
    # --------------------------------------------------------

    expected_technical = (
        (component_tokens | query_tokens)
        & TECHNICAL_TERMS
    )

    technical_match = bool(
        expected_technical & candidate_tokens
    )

    # --------------------------------------------------------
    # Device-category support
    # --------------------------------------------------------

    device_match_count = len(
        device_tokens & candidate_tokens
    )

    device_support = 0.0

    if device_tokens:
        device_support = (
            device_match_count
            / len(device_tokens)
        )

    # --------------------------------------------------------
    # CRITICAL REJECTION RULES
    # --------------------------------------------------------

    # If this is a technical component such as USB, HDMI, VESA,
    # DisplayPort, LVDS, etc., the candidate must actually mention
    # at least one expected technical term.
    if expected_technical and not technical_match:
        return 0.0

    # If the component has meaningful non-generic words, at least
    # one of them must appear in the candidate metadata.
    if component_strong and not strong_component_match:
        return 0.0

    # A component composed almost entirely of generic words
    # ("mounting bracket", "plastic cover", etc.) is dangerous.
    # In that case we require device-category support.
    if not component_strong:
        if device_tokens and device_match_count == 0:
            return 0.0

        # One generic component word alone is not enough.
        generic_matches = (
            component_tokens & candidate_tokens
        )

        if len(generic_matches) < 1:
            return 0.0

    # --------------------------------------------------------
    # Weighted score
    # --------------------------------------------------------

    score = (
        component_coverage * 0.45
        + query_coverage * 0.25
        + device_support * 0.15
        + (0.10 if strong_component_match else 0.0)
        + (0.05 if technical_match else 0.0)
    )

    # Small bonus when both component semantics and device category
    # are represented.
    if (
        strong_component_match
        and device_match_count > 0
    ):
        score += 0.08

    return round(
        min(score, 1.0),
        3,
    )


# ============================================================
# PEXELS SEARCH
# ============================================================

def search_component_image(
    query: str,
    component_name: str,
    device: dict | None = None,
) -> dict | None:

    query = str(query or "").strip()

    if not query:
        return None

    print(
        f'Pexels query: "{query}"',
        flush=True,
    )

    try:
        response = requests.get(
            PEXELS_SEARCH_URL,
            headers={
                "Authorization": PEXELS_API_KEY,
            },
            params={
                "query": query,
                "per_page": PEXELS_RESULTS_PER_QUERY,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        photos = data.get("photos", [])

        if not isinstance(photos, list) or not photos:
            print(
                f'No Pexels results for "{query}".',
                flush=True,
            )
            return None

        # ----------------------------------------------------
        # Score every candidate
        # ----------------------------------------------------

        scored_candidates = []

        for photo in photos:
            if not isinstance(photo, dict):
                continue

            score = score_photo(
                photo=photo,
                component_name=component_name,
                query=query,
                device=device,
            )

            alt = str(
                photo.get("alt") or "untitled"
            ).strip()

            print(
                f'  candidate score={score:.3f}: '
                f'"{alt[:100]}"',
                flush=True,
            )

            scored_candidates.append(
                (score, photo)
            )

        if not scored_candidates:
            print(
                f'No usable Pexels candidates for "{query}".',
                flush=True,
            )
            return None

        scored_candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_photo = scored_candidates[0]

        alt = str(
            best_photo.get("alt") or ""
        ).strip()

        # ----------------------------------------------------
        # Reject uncertain candidates
        # ----------------------------------------------------

        if best_score < MIN_RELEVANCE_SCORE:
            print(
                f'Rejected Pexels candidate '
                f'"{alt or "untitled"}" '
                f'for "{query}" '
                f'(score={best_score:.3f}).',
                flush=True,
            )

            return None

        # ----------------------------------------------------
        # Extract image URLs
        # ----------------------------------------------------

        src = best_photo.get("src", {})

        if not isinstance(src, dict):
            return None

        image_url = (
            src.get("large")
            or src.get("large2x")
            or src.get("original")
        )

        thumbnail_url = (
            src.get("medium")
            or src.get("small")
            or image_url
        )

        if not image_url:
            print(
                f'Pexels candidate for "{query}" '
                "did not contain an image URL.",
                flush=True,
            )
            return None

        # ----------------------------------------------------
        # Accepted
        # ----------------------------------------------------

        print(
            f'Pexels selected "{alt or "untitled"}" '
            f'for "{query}" '
            f'(score={best_score:.3f}).',
            flush=True,
        )

        return {
            "type": "generic_reference",
            "source": "Pexels",
            "query": query,
            "relevance_score": best_score,
            "url": image_url,
            "thumbnail_url": thumbnail_url,
            "photographer": best_photo.get("photographer"),
            "photographer_url": best_photo.get(
                "photographer_url"
            ),
            "pexels_url": best_photo.get("url"),
            "alt": best_photo.get("alt"),
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ) as error:

        print(
            f'Pexels search failed for "{query}": {error}',
            flush=True,
        )

        return None


# ============================================================
# COMPONENT MEDIA ENRICHMENT
# ============================================================

def add_component_images(
    analysis: dict,
    device: dict | None = None,
) -> dict:

    components = analysis.get(
        "components",
        analysis.get(
            "internal_components",
            [],
        ),
    )

    if not isinstance(components, list):
        return analysis

    print(
        "\nSearching Pexels for "
        "generic component images...\n",
        flush=True,
    )

    cache = {}

    for component in components:

        if not isinstance(component, dict):
            continue

        name = str(
            component.get("name") or ""
        ).strip()

        if not name:
            continue

        print(
            f'\nComponent: "{name}"',
            flush=True,
        )

        queries = build_search_queries(
            component=component,
            device=device,
        )

        image = None

        # ----------------------------------------------------
        # Try each conservative query
        # ----------------------------------------------------

        for query in queries:

            cache_key = (
                normalize_text(name),
                normalize_text(query),
                normalize_text(
                    get_device_context(device)
                ),
            )

            if cache_key in cache:
                candidate = cache[cache_key]

            else:
                candidate = search_component_image(
                    query=query,
                    component_name=name,
                    device=device,
                )

                cache[cache_key] = candidate

            if candidate:
                image = candidate
                break

        # ----------------------------------------------------
        # Stable frontend media contract
        # ----------------------------------------------------

        media = component.get("media")

        if not isinstance(media, dict):
            media = {}

        media["image_url"] = (
            image.get("url")
            if image
            else None
        )

        media["thumbnail_url"] = (
            image.get("thumbnail_url")
            if image
            else None
        )

        media["image"] = image

        media.setdefault(
            "model_3d",
            None,
        )

        component["media"] = media

    return analysis