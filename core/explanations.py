"""
core/explanations.py
Generate concise, fund-specific match reasons.
Each reason is a single punchy line — no emoji, plain bullet dot rendered
by the dashboard, no funder name repetition, varied phrasing.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_match_reasons(
    proposal_text: str,
    fund: dict,
    themes: list[dict],
    score: float,
    strength: str = "moderate",
) -> list[str]:
    """
    Return 2–4 short, varied match-reason strings. Each is one tight line.
    The dashboard renders the bullet dot; do NOT prefix with emoji or dashes.

    Strategy:
      1. Focus-area overlap with proposal themes  → most specific
      2. Eligibility signal from proposal text    → org/geo type
      3. Award range fit                          → scale signal
      4. Semantic score confidence                → last resort, only if needed
    """
    reasons: list[str] = []
    proposal_lower = proposal_text.lower()

    focus_areas      = fund.get("focus_areas", [])
    eligibility      = fund.get("eligibility", [])
    award_min        = fund.get("award_min")
    award_max        = fund.get("award_max")
    fund_type        = fund.get("type", "fund")
    focus_lower      = [f.lower() for f in focus_areas]
    eligibility_text = " ".join(eligibility).lower()

    # ── 1. Theme ↔ focus-area overlap ─────────────────────────────────────
    overlapping: list[str] = []
    for theme in themes:
        label = theme.get("label", "").lower()
        label_words = set(label.split())
        for focus in focus_lower:
            if label in focus or focus in label or label_words & set(focus.split()):
                overlapping.append(theme.get("label", ""))
                break

    # deduplicate preserving order
    seen: dict = {}
    unique_overlaps = [seen.setdefault(t, t) for t in overlapping if t not in seen][:2]

    if unique_overlaps and focus_areas:
        themes_str  = " and ".join(unique_overlaps)
        focus_str   = focus_areas[0]
        reasons.append(f"Proposal theme ({themes_str}) aligns with the {focus_str} mandate.")
    elif focus_areas:
        reasons.append(f"Covers {focus_areas[0]} initiatives — matching your project scope.")

    # ── 2. Eligibility signal ──────────────────────────────────────────────
    sig = _eligibility_signal(proposal_lower, eligibility_text)
    if sig:
        reasons.append(sig)

    # ── 3. Award range fit ─────────────────────────────────────────────────
    if award_max and (
        "budget" in proposal_lower or "cost" in proposal_lower or "$" in proposal_text
        or "fund" in proposal_lower or "grant" in proposal_lower
    ):
        if award_min and award_max:
            reasons.append(f"Award range ${award_min:,}–${award_max:,} suits the scale of work described.")
        else:
            reasons.append(f"Up to ${award_max:,} available — adequate for the described initiative.")

    # ── 4. Semantic score (only if we still need a reason) ─────────────────
    if len(reasons) < 2:
        if score >= 0.60:
            reasons.append(f"Strong semantic overlap ({score:.0%}) with this {fund_type}'s objectives.")
        elif score >= 0.45:
            reasons.append(f"Moderate fit ({score:.0%}) — worth a detailed eligibility review.")
        elif score >= 0.35:
            focus_hint = focus_areas[0] if focus_areas else "core focus"
            reasons.append(f"Partial match — strengthen the {focus_hint} framing in your submission.")

    if not reasons:
        return ["Review eligibility and focus areas for a detailed fit assessment."]

    # Cap bullets by match strength
    max_r = 3 if strength == "strong" else (3 if strength == "moderate" else 2)
    min_r = 2 if strength == "strong" else (2 if strength == "moderate" else 1)
    return reasons[:max(min_r, min(max_r, len(reasons)))]


def _eligibility_signal(proposal_lower: str, eligibility_text: str) -> Optional[str]:
    """
    Return one short eligibility-match sentence, or None if nothing specific found.
    Sentences are kept to a single clause — no fund name, no repetition.
    """
    # Indigenous
    if "indigenous" in eligibility_text and any(
        k in proposal_lower for k in ["indigenous", "first nation", "métis", "inuit", "first nations"]
    ):
        return "Indigenous organization eligibility aligns with project's community focus."

    # Municipal
    if any(k in eligibility_text for k in ["municipal", "municipality"]) and any(
        k in proposal_lower for k in ["city", "municipality", "municipal", "town", "county", "region"]
    ):
        return "Municipal applicants are eligible — matches the project's government delivery model."

    # Non-profit
    if any(k in eligibility_text for k in ["non-profit", "nonprofit", "not-for-profit"]) and any(
        k in proposal_lower for k in ["nonprofit", "non-profit", "community organization", "charity", "ngo"]
    ):
        return "Non-profit eligibility matches your organization type."

    # Canadian geography
    if "canadian" in eligibility_text and any(
        k in proposal_lower for k in [
            "canada", "canadian", "ontario", "bc", "british columbia",
            "alberta", "quebec", "nova scotia", "manitoba", "saskatchewan",
            "northwest territories", "yukon", "nunavut", "pei", "newfoundland"
        ]
    ):
        return "Canadian applicant requirement satisfied by the project's geographic context."

    # Innovation / pilot
    if any(k in eligibility_text for k in ["innovation", "pilot", "novel"]) and any(
        k in proposal_lower for k in ["innovative", "pilot", "novel", "new approach", "first-of-its-kind", "demonstration"]
    ):
        return "Pilot or innovative-project eligibility fits the approach described."

    # Small org / SME
    if any(k in eligibility_text for k in ["small", "sme", "startup"]) and any(
        k in proposal_lower for k in ["small", "startup", "sme", "emerging", "early-stage"]
    ):
        return "Open to small organizations — consistent with the proposal's applicant profile."

    return None
