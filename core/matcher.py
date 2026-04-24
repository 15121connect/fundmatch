"""
core/matcher.py
Computes semantic similarity between a proposal embedding and all
fund embeddings, applies deadline filtering, and returns ranked results
with match strength labels. Includes geographic filtering to match proposals
with geographically appropriate funds.
"""

import json
import logging
import re
import numpy as np
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.embedder import encode, encode_proposal
from core.parser import chunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Score thresholds for match strength labels
# Tune these once you have real user feedback on result quality.
# ---------------------------------------------------------------------------
STRONG_THRESHOLD   = 0.70   # cosine similarity ≥ this → "strong"  (score 7-10)
MODERATE_THRESHOLD = 0.40   # ≥ this → "moderate"; below → "weak"  (score 4-6)
MIN_SCORE_THRESHOLD = 0.30  # Only return results above this threshold (score 1-3)


def load_funds(path: str = "data/funds.json") -> list[dict]:
    """Load fund records from JSON. Filters out inactive funds."""
    try:
        with open(path, "r") as f:
            funds = json.load(f)
        active_funds = [f for f in funds if f.get("active", True)]
        logger.info(f"Loaded {len(active_funds)}/{len(funds)} active funds from {path}")
        return active_funds
    except FileNotFoundError:
        logger.error(f"Funds data not found at {path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading funds: {e}")
        return []


def build_fund_index(model, funds: list[dict]) -> np.ndarray:
    """
    Pre-compute and return an embedding matrix for all funds.
    Shape: (n_funds, embedding_dim).

    Call this once at startup (inside @st.cache_resource) and reuse
    the matrix for all queries — don't re-encode on every request.

    The embedding is built from a concatenation of the fund's name,
    focus areas, and description to give the model rich signal.
    """
    texts = [_fund_text(f) for f in funds]
    return encode(model, texts)


def _fund_text(fund: dict) -> str:
    """Construct the text representation of a fund for embedding."""
    focus = ", ".join(fund.get("focus_areas", []))
    eligibility = ", ".join(fund.get("eligibility", []))
    return (
        f"{fund['name']}. "
        f"Focus: {focus}. "
        f"Eligibility: {eligibility}. "
        f"{fund['description']}"
    )


def detect_proposal_country(proposal_text: str) -> Optional[str]:
    """
    Detect the geographic scope of a proposal from its text.
    
    Returns:
        "Canada", "US", "Canada-US", or None (if detection is uncertain)
    
    Detection logic:
    - Look for province names (Ontario, BC, Alberta, etc.) → Canada
    - Look for state names (California, Texas, etc.) → US
    - Look for country keywords ("Canadian", "United States", etc.)
    """
    text_lower = proposal_text.lower()
    
    # Canadian indicators
    ca_provinces = r"\b(ontario|bc|british columbia|alberta|quebec|nova scotia|manitoba|saskatchewan|pei|newfoundland|nwt|yukon|nunavut)\b"
    ca_keywords = r"\b(canadian|canada|canadian organization|canadian nonprofit|provincial|federal government)\b"
    
    # US indicators  
    us_states = r"\b(california|texas|new york|florida|washington|oregon|massachusetts|colorado|minnesota|seattle|portland|los angeles|new york city|san francisco|denver|boston)\b"
    us_keywords = r"\b(united states|us federal|american|nonprofit 501c3|us organization)\b"
    
    ca_matches = len(re.findall(ca_provinces, text_lower)) + len(re.findall(ca_keywords, text_lower))
    us_matches = len(re.findall(us_states, text_lower)) + len(re.findall(us_keywords, text_lower))
    
    # If clear indication of both, return cross-border
    if ca_matches > 0 and us_matches > 0:
        return "Canada-US"
    # If only Canadian indicators
    elif ca_matches > 0:
        return "Canada"
    # If only US indicators
    elif us_matches > 0:
        return "US"
    # Default to None (will include all funds)
    else:
        return None


def _fund_matches_proposal_country(fund: dict, proposal_country: Optional[str]) -> bool:
    """
    Check if a fund is geographically appropriate for the proposal.
    
    Returns:
        True if fund should be included in results
    """
    if proposal_country is None:
        # No country detected; include all funds
        return True
    
    fund_country = fund.get("country", "Canada")
    
    # Exact match
    if proposal_country == fund_country:
        return True
    
    # Fund operates in Canada-US, proposal is either Canada or US
    if fund_country == "Canada-US" and proposal_country in ["Canada", "US"]:
        return True
    
    # Proposal is Canada-US, include all funds that operate in either region
    if proposal_country == "Canada-US":
        return True
    
    return False



def match(
    model,
    proposal_text: str,
    funds: list[dict],
    fund_embeddings: np.ndarray,
    top_n: Optional[int] = None,
    exclude_expired: bool = True,
) -> list[dict]:
    """
    Score and rank funds against a proposal.

    Args:
        model:            Loaded SentenceTransformer.
        proposal_text:    Full cleaned proposal text.
        funds:            List of fund dicts from load_funds().
        fund_embeddings:  Pre-built embedding matrix from build_fund_index().
        top_n:            If set, return only the top N results.
        exclude_expired:  If True, funds with passed deadlines are excluded.

    Returns:
        List of result dicts, sorted by score descending. Each dict contains
        the original fund fields plus:
            score          float 0–1, cosine similarity
            score_out_of_10  int 1–10, for display
            strength       "strong" | "moderate" | "weak"
            days_remaining   int | None (None for rolling deadlines)
            deadline_label   str for display
            
        Results are filtered by:
        - Geographic compatibility (proposal country vs fund country)
        - Score threshold (minimum 0.30 similarity)
        - Expiration status (if exclude_expired=True)
    """
    chunks = chunk(proposal_text, max_words=300, overlap=50)
    proposal_emb = encode_proposal(model, proposal_text, chunks)
    
    # Detect which country/region the proposal is for
    proposal_country = detect_proposal_country(proposal_text)
    logger.info(f"Detected proposal country: {proposal_country}")

    # Cosine similarity — embeddings are L2-normalised so this is a dot product
    scores = (fund_embeddings @ proposal_emb).tolist()

    results = []
    today = date.today()

    for fund, score in zip(funds, scores):
        # Skip if score is below minimum threshold
        if score < MIN_SCORE_THRESHOLD:
            continue
        
        # Skip if fund is not geographically appropriate
        if not _fund_matches_proposal_country(fund, proposal_country):
            logger.debug(f"Skipping {fund['name']} (country mismatch: fund={fund.get('country')}, proposal={proposal_country})")
            continue
        
        days_remaining, deadline_label, deadline_badge = _deadline_info(
            fund.get("deadline"), today
        )

        if exclude_expired and days_remaining is not None and days_remaining < 0:
            continue

        results.append({
            **fund,
            "score":           round(score, 4),
            "score_out_of_10": max(1, min(10, round(score * 10))),
            "score_pct":       min(100, max(0, round(score * 100))),
            "strength":        _strength(score),
            "days_remaining":  days_remaining,
            "deadline_label":  deadline_label,
            "deadline_badge":  deadline_badge,   # "urgent" | "soon" | "later" | "open"
        })

    results.sort(key=lambda r: r["score"], reverse=True)

    if top_n:
        results = results[:top_n]

    logger.info(f"Returned {len(results)} results (filtered from {len(funds)} funds)")
    return results


def summary_stats(results: list[dict]) -> dict:
    """
    Compute the summary numbers shown at the top of the dashboard.

    Returns:
        dict with keys: strong_count, total_count, type_split,
                        closing_soon_count, theme_breakdown
    """
    strong   = [r for r in results if r["strength"] == "strong"]
    moderate = [r for r in results if r["strength"] == "moderate"]
    weak     = [r for r in results if r["strength"] == "weak"]

    # Fund type split (for the stacked bar)
    types = {}
    for r in results:
        t = r.get("type", "other")
        types[t] = types.get(t, 0) + 1

    type_split = {
        t: round(count / len(results) * 100) if results else 0
        for t, count in types.items()
    }

    closing_soon = sum(
        1 for r in results
        if r["days_remaining"] is not None and 0 <= r["days_remaining"] <= 30
    )

    return {
        "strong_count":      len(strong),
        "moderate_count":    len(moderate),
        "weak_count":        len(weak),
        "total_count":       len(results),
        "type_split":        type_split,
        "closing_soon":      closing_soon,
    }


def _strength(score: float) -> str:
    if score >= STRONG_THRESHOLD:
        return "strong"
    elif score >= MODERATE_THRESHOLD:
        return "moderate"
    else:
        return "weak"


def _deadline_info(deadline_str: Optional[str], today: date) -> tuple:
    """
    Parse a deadline string and return display values.

    Returns:
        (days_remaining, deadline_label, deadline_badge)
        days_remaining: int (negative = expired) or None for rolling
        deadline_label: human-readable string
        deadline_badge: "urgent" | "soon" | "later" | "open"

    Display rules:
        - 1–10 days  → show days
        - 1–4 weeks  → show weeks  (11–34 days)
        - 5+ weeks   → show months (35+ days)
    """
    if deadline_str is None:
        return None, "Rolling", "open"

    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        return None, "Rolling", "open"

    days = (deadline - today).days

    if days < 0:
        label = "Expired"
        badge = "urgent"

    # 1–10 days → show days
    elif days <= 10:
        label = f"{days} day{'s' if days != 1 else ''}"
        badge = "urgent"

    # 11–34 days (1–4 weeks) → show weeks
    elif days < 35:
        weeks = max(1, days // 7)
        label = f"{weeks} week{'s' if weeks != 1 else ''}"
        badge = "soon" if weeks <= 2 else "later"

    # 35+ days → show months
    else:
        months = max(1, round(days / 30))
        label = f"{months} month{'s' if months != 1 else ''}"
        badge = "soon" if days <= 60 else "later"

    return days, label, badge