"""
core/themes.py
Extracts thematic categories from a proposal using zero-shot
classification (facebook/bart-large-mnli via HF Inference API
or local pipeline).

Falls back to keyword matching if the HF model is unavailable,
ensuring the app works without an internet connection or API key.
"""

from __future__ import annotations

from typing import Optional


# ---------------------------------------------------------------------------
# Define your theme taxonomy here.
# Keys are internal identifiers; values are the label shown in the UI
# plus candidate phrases fed to the zero-shot classifier.
# ---------------------------------------------------------------------------
THEMES = {
    "clean_energy": {
        "label": "Clean energy",
        "icon": "⚡",
        "candidates": [
            "clean energy", "renewable energy", "solar power", "wind energy",
            "energy efficiency", "heat pump", "battery storage", "green energy",
        ],
    },
    "transportation": {
        "label": "Transportation",
        "icon": "🚌",
        "candidates": [
            "transportation", "electric vehicles", "fleet electrification",
            "public transit", "active transportation", "cycling", "zero-emission",
        ],
    },
    "housing": {
        "label": "Housing",
        "icon": "🏘",
        "candidates": [
            "affordable housing", "housing retrofit", "rental housing",
            "residential", "homelessness", "community housing",
        ],
    },
    "sustainability": {
        "label": "Sustainability",
        "icon": "🌱",
        "candidates": [
            "sustainability", "greenhouse gas", "GHG reduction", "carbon emissions",
            "climate change", "net zero", "Paris Agreement", "circular economy",
        ],
    },
    "food_agriculture": {
        "label": "Food & agriculture",
        "icon": "🌾",
        "candidates": [
            "food security", "agriculture", "farming", "food systems",
            "Indigenous food", "local food", "urban agriculture",
        ],
    },
    "health": {
        "label": "Health",
        "icon": "🏥",
        "candidates": [
            "public health", "mental health", "community health", "healthcare",
            "wellness", "health equity", "health services",
        ],
    },
    "indigenous": {
        "label": "Indigenous communities",
        "icon": "🪶",
        "candidates": [
            "Indigenous", "First Nations", "Métis", "Inuit", "reconciliation",
            "Indigenous-led", "land stewardship",
        ],
    },
    "social_services": {
        "label": "Social services",
        "icon": "🤝",
        "candidates": [
            "social services", "poverty reduction", "employment", "youth",
            "seniors", "disability", "community development",
        ],
    },
}

# Minimum confidence to include a theme (0–1)
CONFIDENCE_THRESHOLD = 0.3

# Maximum themes to surface in the dashboard
MAX_THEMES = 4


def extract_themes(
    proposal_text: str,
    hf_api_token: Optional[str] = None,
    use_local_pipeline: bool = False,
) -> list[dict]:
    """
    Identify the top themes present in a proposal.

    Strategy:
        1. Try zero-shot classification (local pipeline or HF Inference API)
        2. Fall back to keyword scoring if model unavailable

    Args:
        proposal_text:       Clean proposal text.
        hf_api_token:        HF API token for Inference API (optional).
        use_local_pipeline:  If True, load bart-large-mnli locally (needs ~1.5 GB RAM).

    Returns:
        List of up to MAX_THEMES theme dicts, each with:
            id, label, icon, score (0–1), confidence ("high"|"medium"|"low")
        Sorted by score descending.
    """
    theme_labels = [theme["label"] for theme in THEMES.values()]
    theme_ids = list(THEMES.keys())

    scores: dict[str, float] = {}

    if use_local_pipeline:
        scores = _zero_shot_local(proposal_text, theme_labels, theme_ids)
    elif hf_api_token:
        scores = _zero_shot_api(proposal_text, theme_labels, theme_ids, hf_api_token)
    else:
        scores = _keyword_score(proposal_text)

    # Filter and sort
    detected = [
        {
            "id":    tid,
            "label": THEMES[tid]["label"],
            "icon":  THEMES[tid]["icon"],
            "score": round(score, 3),
            "confidence": _confidence_label(score),
        }
        for tid, score in scores.items()
        if score >= CONFIDENCE_THRESHOLD
    ]

    detected.sort(key=lambda x: x["score"], reverse=True)
    return detected[:MAX_THEMES]


def theme_fund_breakdown(theme_id: str, results: list[dict]) -> dict:
    """
    For a given theme, count how many matched funds belong to it
    broken down by match strength.

    Used to populate the mini stacked bars in the theme pills.

    Args:
        theme_id: e.g. "clean_energy"
        results:  Ranked fund list from matcher.match()

    Returns:
        {"strong": int, "moderate": int, "weak": int, "total": int}
    """
    theme_candidates = THEMES.get(theme_id, {}).get("candidates", [])
    if not theme_candidates:
        return {"strong": 0, "moderate": 0, "weak": 0, "total": 0}

    counts = {"strong": 0, "moderate": 0, "weak": 0}
    for fund in results:
        focus = " ".join(fund.get("focus_areas", [])).lower()
        if any(kw.lower() in focus for kw in theme_candidates):
            strength = fund.get("strength", "weak")
            counts[strength] = counts.get(strength, 0) + 1

    counts["total"] = sum(counts.values())
    return counts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _zero_shot_local(text: str, labels: list[str], ids: list[str]) -> dict[str, float]:
    """Run zero-shot classification locally using transformers pipeline."""
    try:
        from transformers import pipeline
        classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )
        # Use a representative excerpt (first 512 words) to keep inference fast
        excerpt = " ".join(text.split()[:512])
        result = classifier(excerpt, candidate_labels=labels, multi_label=True)
        return {
            ids[labels.index(label)]: score
            for label, score in zip(result["labels"], result["scores"])
        }
    except Exception as e:
        print(f"[themes] Local pipeline failed: {e}. Falling back to keyword scoring.")
        return _keyword_score(text)


def _zero_shot_api(
    text: str, labels: list[str], ids: list[str], token: str
) -> dict[str, float]:
    """Call the HF Inference API for zero-shot classification."""
    try:
        import requests
        excerpt = " ".join(text.split()[:512])
        response = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": excerpt, "parameters": {"candidate_labels": labels, "multi_label": True}},
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
        return {
            ids[labels.index(label)]: score
            for label, score in zip(result["labels"], result["scores"])
        }
    except Exception as e:
        print(f"[themes] HF API call failed: {e}. Falling back to keyword scoring.")
        return _keyword_score(text)


def _keyword_score(text: str) -> dict[str, float]:
    """
    Fallback: score themes by counting keyword matches in the proposal.
    Normalises to 0–1 range relative to the most-matched theme.
    """
    text_lower = text.lower()
    raw: dict[str, int] = {}

    for tid, theme in THEMES.items():
        hits = sum(text_lower.count(kw.lower()) for kw in theme["candidates"])
        raw[tid] = hits

    max_hits = max(raw.values()) if raw else 1
    if max_hits == 0:
        return {tid: 0.0 for tid in raw}

    return {tid: round(hits / max_hits, 3) for tid, hits in raw.items()}


def _confidence_label(score: float) -> str:
    if score >= 0.6:
        return "high"
    elif score >= 0.35:
        return "medium"
    return "low"
