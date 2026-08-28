"""
Output grounding checker for MITRE ATT&CK technique IDs.

After the LLM generates an answer, this module:
1. Extracts technique IDs (Txxxx / Txxxx.xxx)
2. Verifies they exist in the local MITRE snapshot
3. Checks whether they are revoked/deprecated
4. Checks whether they are relevant to the retrieved context
5. Returns a structured classification for each ID

Design notes:
- Fully deterministic and CPU-only
- Uses a local slim snapshot (no network calls at check time)
- Relevance is measured against the retrieved documents, not the user query
- Taxonomy: FABRICATED / REVOKED / REAL_BUT_IRRELEVANT / REAL_AND_PLAUSIBLE / UNVERIFIED
"""

import json
import os
import re
from functools import lru_cache
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SNAPSHOT_PATH = os.path.join(
    "data", "mitre_attack", "enterprise_attack_techniques.json"
)

# Minimum topical overlap to consider a real technique "plausible"
# for the current retrieved context. Keep conservative for the first version.
OVERLAP_THRESHOLD = 0.40

# ---------------------------------------------------------------------------
# Snapshot loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_attack_techniques(snapshot_path: str = DEFAULT_SNAPSHOT_PATH) -> dict:
    """
    Load the slim technique snapshot once and cache it in memory.
    Returns a dict: technique_id -> {name, description, revoked, url}
    """
    if not os.path.exists(snapshot_path):
        # Caller can decide how to handle a missing snapshot
        return {}

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("techniques", {})


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_attack_ids(text: str) -> set[str]:
    """
    Extract MITRE ATT&CK technique IDs from free text.
    Matches both techniques (T1055) and sub-techniques (T1055.011).
    Normalises to uppercase.
    """
    if not text:
        return set()

    pattern = r"\bT\d{4}(?:\.\d{3})?\b"
    return {m.upper() for m in re.findall(pattern, text, flags=re.IGNORECASE)}


# ---------------------------------------------------------------------------
# Lightweight topical overlap (deterministic, no embeddings)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "to", "and", "or", "is", "was",
    "for", "with", "that", "this", "by", "as", "be", "are", "from", "at",
    "attack", "attacker", "adversary", "adversaries", "technique",
    "detected", "allows", "allow", "via", "used", "known", "may", "can",
}


def _stem(word: str) -> str:
    """Very lightweight suffix stripping — good enough for security prose."""
    suffixes = [
        "ation", "ition", "ment", "ness", "ing", "ers", "ies", "ied",
        "ion", "ive", "ily", "ers", "ing", "ed", "ly", "er", "es", "s",
    ]
    w = word.lower()
    for suf in suffixes:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    if w.endswith("e") and len(w) > 4:
        return w[:-1]
    return w


def _topical_overlap(text_a: str, text_b: str) -> float:
    """
    Fraction of significant stems in text_a that also appear in text_b.
    Used to decide whether a real technique is relevant to the retrieved context.
    """
    def significant_stems(t: str) -> set[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", (t or "").lower())
        return {_stem(w) for w in words if w not in _STOPWORDS}

    stems_a = significant_stems(text_a)
    stems_b = significant_stems(text_b)

    if not stems_a or not stems_b:
        return 0.0

    return len(stems_a & stems_b) / len(stems_a)


# ---------------------------------------------------------------------------
# Core verification
# ---------------------------------------------------------------------------

def verify_technique(
    technique_id: str,
    retrieved_context: str,
    snapshot_path: str = DEFAULT_SNAPSHOT_PATH,
) -> dict:
    """
    Verify a single technique ID against the local snapshot and the
    retrieved context.

    Returns a dict with:
        technique_id, classification, name, topical_overlap, url
    """
    technique_id = (technique_id or "").upper()
    techniques = _load_attack_techniques(snapshot_path)

    if not techniques:
        return {
            "technique_id": technique_id,
            "classification": "UNVERIFIED",
            "name": None,
            "topical_overlap": None,
            "url": None,
        }

    info = techniques.get(technique_id)

    if info is None:
        return {
            "technique_id": technique_id,
            "classification": "FABRICATED",
            "name": None,
            "topical_overlap": None,
            "url": None,
        }

    if info.get("revoked"):
        return {
            "technique_id": technique_id,
            "classification": "REVOKED",
            "name": info.get("name"),
            "topical_overlap": None,
            "url": info.get("url"),
        }

    # Real and currently valid → measure relevance to retrieved context
    description = info.get("description") or ""

    # Returns fraction of significant words in the retrieved context that also appear in the technique description
    overlap = _topical_overlap(retrieved_context, description)

    if overlap >= OVERLAP_THRESHOLD:
        classification = "REAL_AND_PLAUSIBLE"
    else:
        classification = "REAL_BUT_IRRELEVANT"

    return {
        "technique_id": technique_id,
        "classification": classification,
        "name": info.get("name"),
        "topical_overlap": round(overlap, 3),
        "url": info.get("url"),
    }


def check_attack_grounding(
    answer: str,
    retrieved_docs: list[str],
    snapshot_path: str = DEFAULT_SNAPSHOT_PATH,
) -> dict:
    """
    Main entry point used by the RAG pipeline.

    Parameters
    ----------
    answer : str
        The text generated by the LLM.
    retrieved_docs : list[str]
        The documents (or redacted chunks) that were given to the LLM
        as context. Relevance is measured against these, not against
        the original user query.

    Returns
    -------
    dict with:
        technique_ids          - all IDs found in the answer
        verifications          - list of per-ID results
        ungrounded             - IDs that are not REAL_AND_PLAUSIBLE
        requires_review        - True if any ID needs human attention
        flagged                - True if any problematic citation exists
    """
    technique_ids = extract_attack_ids(answer)

    if not technique_ids:
        return {
            "technique_ids": [],
            "verifications": [],
            "ungrounded": [],
            "requires_review": False,
            "flagged": False,
        }

    # Concatenate retrieved documents into one context string
    retrieved_context = "\n\n".join(retrieved_docs or [])

    verifications = [
        verify_technique(tid, retrieved_context, snapshot_path)
        for tid in sorted(technique_ids)
    ]

    # Any classification other than a clean grounded citation needs review
    ungrounded = [
        v["technique_id"]
        for v in verifications
        if v["classification"] != "REAL_AND_PLAUSIBLE"
    ]

    # Only require review when something is actually ungrounded
    flagged = len(ungrounded) > 0
    requires_review = flagged

    return {
        "technique_ids": sorted(technique_ids),
        "verifications": verifications,
        "ungrounded": ungrounded,
        "requires_review": requires_review,
        "flagged": flagged,
    }


# ---------------------------------------------------------------------------
# Optional helper: simple inline annotation
# ---------------------------------------------------------------------------

def annotate_answer(answer: str, verifications: list[dict]) -> str:
    """
    Tag ungrounded technique IDs in answer text.

    Longer IDs are applied first. A shorter ID (T1055) must not match as a
    prefix of a sub-technique (T1055.011).
    """
    if not answer or not verifications:
        return answer

    tags = {
        v["technique_id"]: v["classification"]
        for v in verifications
        if v.get("classification") and v["classification"] != "REAL_AND_PLAUSIBLE"
    }
    if not tags:
        return answer

    annotated = answer

    for tid in sorted(tags.keys(), key=len, reverse=True):
        classification = tags[tid]
        # Do not match inside a longer ID: T1055 must not match T1055.011
        pattern = re.compile(
            rf"(?<![A-Za-z0-9.]){re.escape(tid)}(?!\.\d)(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        annotated = pattern.sub(
            f"{tid} [⚠ {classification}]",
            annotated,
        )

    return annotated