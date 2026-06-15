"""
AI Moderation Service
Uses unitary/toxic-bert via HuggingFace pipeline.
Falls back to enhanced keyword-based scoring if model unavailable.
"""
from typing import Optional, cast, Any
import logging
import re

logger = logging.getLogger(__name__)

_pipeline = None

# ---------------------------------------------------------------------------
# Keyword-based fallback — now uses whole-word matching and category weights
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "threat": [
        "kill", "murder", "stab", "shoot", "hurt", "attack", "destroy",
        "bomb", "blow up", "beat you", "come for you", "i will find you",
        "you're dead", "you are dead", "die", "suffer"
    ],
    "hate_speech": [
        "racist", "racism", "bigot", "nazi", "inferior race", "white supremac",
        "slur", "n-word", "hate all", "go back to your country",
    ],
    "harassment": [
        "loser", "pathetic", "worthless", "stupid", "idiot", "moron", "ugly",
        "nobody likes you", "kill yourself", "kys", "you suck", "shut up",
        "get lost", "waste of space", "freak", "creep", "gtfo",
    ],
    "insult": [
        "dumb", "trash", "garbage", "disgusting", "gross", "pig", "fat",
        "nasty", "scum", "piece of shit", "go to hell",
    ],
    "profanity": [
        "fuck", "shit", "bitch", "asshole", "bastard", "crap", "damn",
        "hell", "ass", "wtf", "stfu",
    ],
    "cyberbullying": [
        "everyone hates you", "no one likes you", "you have no friends",
        "you should be ashamed", "delete yourself", "end yourself", "kys",
    ],
}

# Severity multiplier per category (higher = worse)
CATEGORY_WEIGHT = {
    "threat": 1.0,
    "hate_speech": 0.95,
    "cyberbullying": 0.9,
    "harassment": 0.8,
    "insult": 0.7,
    "profanity": 0.5,
}


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from transformers import pipeline
        _pipeline = pipeline(
            "text-classification",
            model="unitary/toxic-bert",
            top_k=None,
            truncation=True,
            max_length=512,
        )
        logger.info("Loaded unitary/toxic-bert")
    except Exception as e:
        logger.warning(f"Could not load toxic-bert: {e}. Using keyword fallback.")
        _pipeline = "fallback"
    return _pipeline


def _keyword_score(text: str) -> dict:
    """
    Enhanced keyword fallback that:
    - Uses whole-word boundary matching to avoid false positives
    - Weights hits by category severity
    - Returns a composite score capped at 1.0
    """
    text_lower = text.lower()
    category_scores: dict[str, float] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        weight = CATEGORY_WEIGHT.get(category, 0.6)
        hits = 0
        for kw in keywords:
            # Multi-word phrases: substring match is fine
            if " " in kw:
                if kw in text_lower:
                    hits += 2  # phrase hit counts double
            else:
                # Single word: require word boundary to avoid "classic" matching "ass"
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    hits += 1

        if hits > 0:
            score = min(hits * 0.25 * weight, 1.0)
            category_scores[category] = round(score, 3)

    if not category_scores:
        return {"toxicity_score": 0.0, "category": "safe", "confidence": 1.0}

    top_category = max(category_scores, key=lambda k: category_scores[k])
    top_score = category_scores[top_category]

    # Composite toxicity: weighted average of all triggered categories
    overall = min(sum(category_scores.values()), 1.0)

    return {
        "toxicity_score": round(overall, 3),
        "category": top_category,
        "confidence": round(top_score, 3),
    }


def classify_text(text: str) -> dict:
    """
    Returns: { toxicity_score: float, category: str, confidence: float }
    toxicity_score: 0-1 where >0.3 = flagged, >0.7 = critical
    """
    if not text or not text.strip():
        return {"toxicity_score": 0.0, "category": "safe", "confidence": 1.0}

    # Very short texts (< 2 chars) can't be meaningfully analyzed
    if len(text.strip()) < 2:
        return {"toxicity_score": 0.0, "category": "safe", "confidence": 1.0}

    pipe = _load_pipeline()

    if pipe == "fallback":
        return _keyword_score(text)

    try:
        results = cast(list[dict[str, Any]], pipe(text[:512])[0])
        label_map = {r["label"].lower(): r["score"] for r in results}

        toxic_score    = label_map.get("toxic", 0.0)
        threat_score   = label_map.get("threat", 0.0)
        insult_score   = label_map.get("insult", 0.0)
        identity_hate  = label_map.get("identity_hate", 0.0)
        obscene        = label_map.get("obscene", 0.0)
        severe_toxic   = label_map.get("severe_toxic", 0.0)

        scores = {
            "threat":      threat_score   * CATEGORY_WEIGHT["threat"],
            "hate_speech": identity_hate  * CATEGORY_WEIGHT["hate_speech"],
            "harassment":  insult_score   * CATEGORY_WEIGHT["harassment"],
            "profanity":   obscene        * CATEGORY_WEIGHT["profanity"],
            "toxic":       toxic_score,
            "severe_toxic": severe_toxic,
        }

        top_category = max(scores, key=lambda k: scores[k])
        top_score = scores[top_category]

        # Composite score: severe_toxic is a strong signal
        overall = max(
            toxic_score,
            severe_toxic * 0.95,
            threat_score * CATEGORY_WEIGHT["threat"],
            identity_hate * CATEGORY_WEIGHT["hate_speech"],
        )

        if top_score < 0.15:
            top_category = "safe"

        # Keyword boost and specific category fallback:
        # If model confidence is low, or if it just gave a generic "toxic" label,
        # use the keyword results to give a more descriptive category and boost score.
        kw_result = _keyword_score(text)
        if kw_result["toxicity_score"] > overall and kw_result["toxicity_score"] > 0.3:
            overall = max(overall, kw_result["toxicity_score"] * 0.8)
            
        if top_category == "safe" or (top_category == "toxic" and kw_result["category"] != "safe"):
            top_category = kw_result["category"]

        return {
            "toxicity_score": round(min(overall, 1.0), 3),
            "category": top_category,
            "confidence": round(top_score, 3),
        }
    except Exception as e:
        logger.error(f"Moderation error: {e}")
        return _keyword_score(text)
