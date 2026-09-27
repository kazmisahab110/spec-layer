import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

env_path = (
    Path(__file__).resolve().parents[3]
    / ".env"
)

load_dotenv(env_path)

SKETCHFAB_API_KEY = os.getenv(
    "SKETCHFAB_API_KEY"
)

if not SKETCHFAB_API_KEY:
    raise ValueError(
        "SKETCHFAB_API_KEY was not found in .env"
    )


SKETCHFAB_SEARCH_URL = (
    "https://api.sketchfab.com/v3/search"
)


# ---------------------------------------------------------
# Generic relevance settings
# ---------------------------------------------------------

# The ranking algorithm intentionally knows NOTHING about
# monitors, cars, phones, keyboards, pumps, etc.
#
# It only evaluates whether the returned model metadata
# actually matches the dynamically generated query.

MIN_RELEVANCE_SCORE = 0.55

MIN_QUERY_COVERAGE = 0.50


# ---------------------------------------------------------
# Text helpers
# ---------------------------------------------------------

def _tokens(text: str) -> set[str]:
    """
    Normalize arbitrary text into searchable tokens.
    """

    if not text:
        return set()

    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            str(text).lower()
        )
        if len(token) > 1
    }


def _get_thumbnail(
    model: dict
) -> str | None:

    thumbnails = (
        model.get("thumbnails")
        or {}
    )

    images = thumbnails.get(
        "images",
        []
    )

    if not images:
        return None

    largest = max(
        images,
        key=lambda image: image.get(
            "width",
            0
        )
    )

    return largest.get("url")


def _model_text(
    model: dict
) -> tuple[str, str, str]:

    name = (
        model.get("name")
        or ""
    )

    description = (
        model.get("description")
        or ""
    )

    tags = (
        model.get("tags")
        or []
    )

    tag_text = " ".join(
        tag.get("name", "")
        if isinstance(tag, dict)
        else str(tag)
        for tag in tags
    )

    return (
        name,
        description,
        tag_text
    )


# ---------------------------------------------------------
# Generic relevance scoring
# ---------------------------------------------------------

def _score_model(
    model: dict,
    query: str
) -> dict:
    """
    Evaluate how completely a Sketchfab result matches the
    dynamically generated component query.

    No component vocabulary is hardcoded.

    Name matches matter most.
    Tags provide secondary evidence.
    Description text provides weak evidence.
    """

    query_tokens = _tokens(query)

    if not query_tokens:
        return {
            "score": 0.0,
            "coverage": 0.0,
            "matched_tokens": set(),
        }

    (
        name,
        description,
        tag_text
    ) = _model_text(model)

    name_tokens = _tokens(name)
    tag_tokens = _tokens(tag_text)
    description_tokens = _tokens(
        description
    )

    # -----------------------------------------------------
    # Determine which query concepts are actually present.
    # -----------------------------------------------------

    strong_tokens = (
        name_tokens
        | tag_tokens
    )

    all_metadata_tokens = (
        strong_tokens
        | description_tokens
    )

    matched_tokens = (
        query_tokens
        & all_metadata_tokens
    )

    strong_matches = (
        query_tokens
        & strong_tokens
    )

    name_matches = (
        query_tokens
        & name_tokens
    )

    # -----------------------------------------------------
    # Query coverage
    # -----------------------------------------------------

    coverage = (
        len(matched_tokens)
        / len(query_tokens)
    )

    strong_coverage = (
        len(strong_matches)
        / len(query_tokens)
    )

    name_coverage = (
        len(name_matches)
        / len(query_tokens)
    )

    # -----------------------------------------------------
    # Weighted relevance
    # -----------------------------------------------------

    score = (
        name_coverage * 0.60
        + strong_coverage * 0.25
        + coverage * 0.15
    )

    # -----------------------------------------------------
    # Phrase matching
    # -----------------------------------------------------

    normalized_query = " ".join(
        str(query).lower().split()
    )

    normalized_name = " ".join(
        name.lower().split()
    )

    if (
        normalized_query
        and normalized_query
        == normalized_name
    ):
        score += 0.35

    elif (
        normalized_query
        and normalized_query
        in normalized_name
    ):
        score += 0.20

    # -----------------------------------------------------
    # Important mismatch penalty
    #
    # If a multi-word query only matches one concept,
    # do not reward it simply because that word appears
    # strongly in the candidate name.
    # -----------------------------------------------------

    if (
        len(query_tokens) >= 2
        and coverage < 0.50
    ):
        score *= 0.35

    # A result whose name contains NONE of the query terms
    # should almost never win based only on description text.
    # -----------------------------------------------------
# Candidate-name validation
#
# Metadata can contain query words incidentally.
# A candidate should therefore have meaningful overlap
# with the model's actual title, not only its tags or
# description.
# -----------------------------------------------------

    name_coverage = (
        len(name_matches)
        / len(query_tokens)
    )

    if not name_matches:
        score *= 0.25

    elif (
        len(query_tokens) >= 2
        and name_coverage < 0.50
    ):
        score *= 0.45
    return {
        "score": score,
        "coverage": coverage,
        "matched_tokens": matched_tokens,
    }


# ---------------------------------------------------------
# Sketchfab API
# ---------------------------------------------------------

def _search_sketchfab(
    query: str
) -> list:

    headers = {
        "Authorization":
            f"Bearer {SKETCHFAB_API_KEY}"
    }

    params = {
        "type": "models",
        "q": query,
        "count": 24,
    }

    try:

        response = requests.get(
            SKETCHFAB_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "results",
            []
        )

    except requests.RequestException as error:

        print(
            f'Sketchfab search failed for '
            f'"{query}": {error}',
            flush=True
        )

        return []

    except ValueError as error:

        print(
            f'Sketchfab returned invalid JSON '
            f'for "{query}": {error}',
            flush=True
        )

        return []


# ---------------------------------------------------------
# Output formatting
# ---------------------------------------------------------

def _format_model(
    model: dict,
    query: str,
    relevance: dict
) -> dict | None:

    uid = model.get("uid")
    
    if not uid:
        return None

    user = (
        model.get("user")
        or {}
    )

    license_info = (
        model.get("license")
        or {}
    )

    return {
        "type": "generic_reference",

        "source": "Sketchfab",

        "query": query,

        "relevance_score": round(
            relevance["score"],
            3
        ),

        "query_coverage": round(
            relevance["coverage"],
            3
        ),

        "matched_query_terms": sorted(
            relevance["matched_tokens"]
        ),

        "uid": uid,

        "name": model.get("name"),

        "model_url": (
            f"https://sketchfab.com/"
            f"models/{uid}"
        ),

        "viewer_url": (
            f"https://sketchfab.com/"
            f"models/{uid}/embed"
        ),

        "thumbnail_url":
            _get_thumbnail(model),

        "author": (
            user.get("displayName")
            or user.get("username")
        ),

        "author_url": (
            f"https://sketchfab.com/"
            f"{user.get('username')}"
            if user.get("username")
            else None
        ),

        "license":
            license_info.get("label"),

        "license_url":
            license_info.get("url"),

        "description":
            model.get("description"),

        "view_count":
            model.get("viewCount"),

        "like_count":
            model.get("likeCount"),

        # We reference/embed the model.
        # We do not download it.
        "downloaded": False,

    "name_query_coverage": round(
        len(
            _tokens(query)
            & _tokens(model.get("name", ""))
        )
        / len(_tokens(query)),
        3
    ) if _tokens(query) else 0.0,

    }


# ---------------------------------------------------------
# Public model search
# ---------------------------------------------------------

def search_component_model(
    query: str
) -> dict | None:
    """
    Find a generic 3D reference for an arbitrary physical
    component.

    The query is generated upstream by the documentation
    interpreter.

    This function contains no product-specific rules.
    """

    query = str(
        query or ""
    ).strip()

    if not query:
        return None

    print(
        f'Sketchfab query: "{query}"',
        flush=True
    )

    results = _search_sketchfab(
        query
    )

    candidates = []

    for model in results:

        if not model.get("uid"):
            continue

        relevance = _score_model(
            model=model,
            query=query
        )

        candidates.append({
            "model": model,
            "relevance": relevance,
        })

    if not candidates:

        print(
            f'No Sketchfab results for '
            f'"{query}".',
            flush=True
        )

        return None

    candidates.sort(
        key=lambda candidate:
            candidate["relevance"]["score"],
        reverse=True
    )

    best = candidates[0]

    model = best["model"]
    relevance = best["relevance"]

    score = relevance["score"]
    coverage = relevance["coverage"]

    # -----------------------------------------------------
    # Reject weak semantic matches.
    # -----------------------------------------------------

    name_tokens = _tokens(
        model.get("name", "")
    )

    query_tokens = _tokens(query)

    name_matches = (
        query_tokens
        & name_tokens
    )

    name_coverage = (
        len(name_matches)
        / len(query_tokens)
        if query_tokens
        else 0.0
    )

    if (
        score < MIN_RELEVANCE_SCORE
        or coverage < MIN_QUERY_COVERAGE
        or (
            len(query_tokens) >= 2
            and name_coverage < 0.50
        )
    ):

        print(
            f'Rejected Sketchfab candidate '
            f'"{model.get("name")}" '
            f'for "{query}" '
            f'(score={score:.3f}, '
            f'coverage={coverage:.3f}).',
            flush=True
        )

        return None

    print(
        f'Sketchfab selected '
        f'"{model.get("name")}" '
        f'for "{query}" '
        f'(score={score:.3f}, '
        f'coverage={coverage:.3f}).',
        flush=True
    )

    return _format_model(
        model=model,
        query=query,
        relevance=relevance
    )


# ---------------------------------------------------------
# Pipeline enrichment
# ---------------------------------------------------------

def add_component_models(
    analysis: dict,
    device: dict | None = None
) -> dict:
    """
    Add a generic Sketchfab 3D reference to each documented
    internal component.

    No models are downloaded.

    If no sufficiently relevant generic model exists,
    model_3d is deliberately left as None.
    """

    components = analysis.get(
    "components",
    analysis.get("internal_components", []),
    )

    if not isinstance(
        components,
        list
    ):
        return analysis

    print(
        "\nSearching Sketchfab for generic "
        "3D component models...\n",
        flush=True
    )

    cache = {}

    for component in components:

        if not isinstance(
            component,
            dict
        ):
            continue

        component_name = (
            component.get("name")
        )

        if not component_name:
            continue

        # The interpreter dynamically generates this.
        #
        # Falling back to the documented component name
        # remains completely product-agnostic.
        query = (
            component.get(
                "generic_3d_query"
            )
            or component_name
        )

        query = str(
            query
        ).strip()

        component[
            "generic_3d_query"
        ] = query

        print(
            f'Component: "{component_name}" '
            f'-> "{query}"',
            flush=True
        )

        if query in cache:

            model = cache[query]

        else:

            model = search_component_model(
                query
            )

            cache[query] = model

        media = component.get(
            "media"
        )

        if not isinstance(
            media,
            dict
        ):
            media = {}

        media["model_3d"] = model

        component["media"] = media

    return analysis