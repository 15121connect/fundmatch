"""
core/eligibility.py
AI-powered eligibility verification using zero-shot classification.
Checks if a proposal meets each fund's stated eligibility criteria.
"""

import logging
from typing import Optional
from transformers import pipeline

logger = logging.getLogger(__name__)

# Cache the classifier
_classifier = None


def get_classifier():
    """Load zero-shot classifier once."""
    global _classifier
    if _classifier is None:
        try:
            _classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1  # CPU; set to 0 for GPU
            )
            logger.info("Loaded zero-shot classifier for eligibility checks")
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")
            return None
    return _classifier


def verify_eligibility(
    proposal_text: str,
    eligibility_criteria: list[str],
) -> list[dict]:
    """
    Check if a proposal satisfies each eligibility criterion using zero-shot classification.
    
    Args:
        proposal_text:        Full proposal text (at least 100 chars for reliable classification)
        eligibility_criteria: List of eligibility statements (e.g., "Canadian nonprofit", "minimum 10 units")
    
    Returns:
        List of dicts with keys:
        - criterion: str, the original eligibility statement
        - status: "✓" (pass), "✗" (fail), "?" (uncertain)
        - confidence: float 0-1, classification confidence
        - reasoning: str, brief explanation
    """
    if not eligibility_criteria or not proposal_text:
        return []
    
    classifier = get_classifier()
    if classifier is None:
        # Fallback: return uncertain status
        return [
            {
                "criterion": c,
                "status": "?",
                "confidence": 0.0,
                "reasoning": "Classifier unavailable; manual review recommended."
            }
            for c in eligibility_criteria
        ]
    
    # Truncate proposal to first 512 tokens for efficiency (classifier token limit ~1024)
    words = proposal_text.split()[:400]  # ~400 words ≈ 800 tokens
    truncated_proposal = " ".join(words)
    
    results = []
    
    try:
        for criterion in eligibility_criteria:
            # Use zero-shot to classify: does the proposal satisfy this criterion?
            output = classifier(
                truncated_proposal,
                [criterion, f"Not {criterion}"],
                multi_label=False,
            )
            
            # Extract classification results
            labels = output.get("labels", [])
            scores = output.get("scores", [])
            
            if labels and scores:
                # If top label is the criterion with >60% confidence, it's a pass
                if labels[0] == criterion and scores[0] > 0.55:
                    status = "✓"
                    reasoning = f"Proposal clearly satisfies this criterion ({scores[0]:.0%} confidence)."
                # If top label is "Not criterion" with >60% confidence, it's a fail
                elif labels[0] != criterion and scores[0] > 0.55:
                    status = "✗"
                    reasoning = f"Proposal does not appear to satisfy this criterion ({scores[0]:.0%} confidence)."
                # Otherwise uncertain
                else:
                    status = "?"
                    reasoning = f"Unclear from proposal text ({scores[0]:.0%} confidence)."
            else:
                status = "?"
                reasoning = "Classification failed; manual review recommended."
            
            results.append({
                "criterion": criterion,
                "status": status,
                "confidence": scores[0] if scores else 0.0,
                "reasoning": reasoning,
            })
    
    except Exception as e:
        logger.error(f"Eligibility check error: {e}")
        return [
            {
                "criterion": c,
                "status": "?",
                "confidence": 0.0,
                "reasoning": f"Error during check: {str(e)}"
            }
            for c in eligibility_criteria
        ]
    
    return results
