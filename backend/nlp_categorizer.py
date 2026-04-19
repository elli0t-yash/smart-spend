"""
Phase 2 – Sentence-transformer semantic categorization.

Used as a second-pass categorizer when keyword rules in categorizer.py return "Other".
Embeds the transaction text and finds the closest category via cosine similarity.
Falls back silently if sentence-transformers is not installed.
"""
from __future__ import annotations
from functools import lru_cache

# One representative sentence per category — richer = better recall
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "Food & Dining":      "restaurant food delivery dining cafe grocery supermarket meal swiggy zomato blinkit",
    "Transport":          "taxi cab ride uber ola metro train flight bus travel commute fuel petrol",
    "Shopping":           "online shopping ecommerce retail clothing fashion electronics amazon flipkart",
    "Entertainment":      "streaming music movies web series subscription gaming netflix spotify hotstar",
    "Health & Fitness":   "pharmacy medicine hospital doctor gym fitness health wellness clinic",
    "Utilities":          "electricity mobile recharge internet broadband gas water utility bill airtel jio",
    "Salary":             "salary income payroll wages credit from employer",
    "Interest / Returns": "interest income return investment fixed deposit dividend",
    "Transfer / P2P":     "peer to peer transfer personal payment send money friend family gpay phonepe paytm",
}

_THRESHOLD = 0.30   # minimum cosine similarity to accept a label


@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


@lru_cache(maxsize=1)
def _category_embeddings():
    """Pre-compute and cache embeddings for all category descriptions."""
    model = _load_model()
    if model is None:
        return None, None
    import numpy as np
    categories = list(CATEGORY_DESCRIPTIONS.keys())
    descriptions = list(CATEGORY_DESCRIPTIONS.values())
    embeddings = model.encode(descriptions, normalize_embeddings=True)
    return categories, np.array(embeddings)


def semantic_categorize(text: str) -> str | None:
    """
    Return the best-matching category for `text`, or None if confidence is too low
    or the model is unavailable.
    """
    model = _load_model()
    if model is None:
        return None

    categories, cat_embeddings = _category_embeddings()
    if categories is None:
        return None

    import numpy as np
    txn_emb = model.encode([text], normalize_embeddings=True)
    scores: list[float] = (txn_emb @ cat_embeddings.T)[0].tolist()
    best_idx = int(np.argmax(scores))
    best_score = scores[best_idx]

    if best_score >= _THRESHOLD:
        return categories[best_idx]
    return None


def is_semantic_available() -> bool:
    return _load_model() is not None
