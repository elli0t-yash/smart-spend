"""
Phase 1 – spaCy NER-based merchant extraction.

Used as a fallback when regex-based extraction in parser.py returns a weak/noisy
result (too long, all-caps noise, or hits the generic truncation path).
"""
from __future__ import annotations
from functools import lru_cache

_MODEL_NAME = "en_core_web_sm"


@lru_cache(maxsize=1)
def _load_nlp():
    try:
        import spacy
        return spacy.load(_MODEL_NAME)
    except Exception:
        return None


def ner_extract_merchant(text: str) -> str | None:
    """
    Run spaCy NER on `text` and return the first ORG entity found, or None
    if spaCy is unavailable or finds nothing useful.
    """
    nlp = _load_nlp()
    if not nlp:
        return None

    doc = nlp(text[:200])
    for ent in doc.ents:
        if ent.label_ == "ORG":
            name = ent.text.strip()
            if len(name) >= 3 and not name.isdigit():
                return name.title()
    return None


def extract_entities(text: str) -> dict[str, str | None]:
    """Return all detected entities (ORG, MONEY, DATE) from a narration string."""
    nlp = _load_nlp()
    if not nlp:
        return {"org": None, "money": None, "date": None}

    doc = nlp(text[:200])
    result: dict[str, str | None] = {"org": None, "money": None, "date": None}
    for ent in doc.ents:
        if ent.label_ == "ORG" and result["org"] is None:
            result["org"] = ent.text.strip()
        elif ent.label_ == "MONEY" and result["money"] is None:
            result["money"] = ent.text.strip()
        elif ent.label_ == "DATE" and result["date"] is None:
            result["date"] = ent.text.strip()
    return result


def is_spacy_available() -> bool:
    return _load_nlp() is not None
