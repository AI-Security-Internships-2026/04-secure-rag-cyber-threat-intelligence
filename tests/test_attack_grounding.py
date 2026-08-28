"""
Unit tests for src/attack_grounding.py

Covers:
- ID extraction (normal, sub-technique, case, edge cases)
- Existence / fabricated detection
- Revoked detection
- Relevance scoring (plausible vs irrelevant)
- End-to-end check_attack_grounding behaviour
- Annotation helper
- Missing snapshot handling

All tests that need technique data use a controlled in-memory mock
so the suite does not depend on the real snapshot file being present.

Run: pytest tests/test_attack_grounding.py -v
"""

import json
import os
import pytest
from pathlib import Path

# Make sure we can import from src/
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from attack_grounding import (
    extract_attack_ids,
    verify_technique,
    check_attack_grounding,
    annotate_answer,
    _load_attack_techniques,
    OVERLAP_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_snapshot(monkeypatch):
    """Provide a tiny, controlled technique dictionary for tests."""
    techniques = {
        "T1055": {
            "name": "Process Injection",
            "description": (
                "Adversaries may inject code into processes in order to evade "
                "process-based defenses and potentially elevate privileges. "
                "Process injection is a method of executing arbitrary code."
            ),
            "revoked": False,
            "url": "https://attack.mitre.org/techniques/T1055",
        },
        "T1055.011": {
            "name": "Extra Window Memory Injection",
            "description": "Adversaries may inject into extra window memory.",
            "revoked": False,
            "url": "https://attack.mitre.org/techniques/T1055/011",
        },
        "T1086": {
            "name": "PowerShell",
            "description": "This technique has been deprecated.",
            "revoked": True,
            "url": "https://attack.mitre.org/techniques/T1086",
        },
    }

    def _fake_load(snapshot_path=None):
        return techniques

    monkeypatch.setattr("attack_grounding._load_attack_techniques", _fake_load)
    return techniques


# ---------------------------------------------------------------------------
# 1. Extraction tests
# ---------------------------------------------------------------------------

def test_extract_standard_technique():
    assert extract_attack_ids("This maps to T1055 process injection.") == {"T1055"}


def test_extract_subtechnique():
    assert extract_attack_ids("Seen with T1055.011.") == {"T1055.011"}


def test_extract_case_insensitive():
    assert extract_attack_ids("consistent with t1055 and T1059.001") == {"T1055", "T1059.001"}


def test_extract_multiple():
    text = "Related to T1055 and also T1059.001 plus T1486."
    assert extract_attack_ids(text) == {"T1055", "T1059.001", "T1486"}


def test_extract_ignores_embedded_ids():
    # Must not match inside a larger token
    assert extract_attack_ids("HOSTT1055XYZ was affected.") == set()


def test_extract_empty_and_none():
    assert extract_attack_ids("") == set()
    assert extract_attack_ids(None) == set()


# ---------------------------------------------------------------------------
# 2. verify_technique – classification branches
# ---------------------------------------------------------------------------

def test_fabricated_when_id_missing(mock_snapshot):
    result = verify_technique("T9999", "some retrieved context about injection")
    assert result["classification"] == "FABRICATED"
    assert result["name"] is None


def test_revoked_technique(mock_snapshot):
    result = verify_technique("T1086", "powershell activity observed")
    assert result["classification"] == "REVOKED"
    assert result["name"] == "PowerShell"


def test_real_and_plausible(mock_snapshot):
    context = (
        "Suspicious code injection into a running process. "
        "The adversary appears to be using process injection techniques."
    )
    result = verify_technique("T1055", context)
    assert result["classification"] == "REAL_AND_PLAUSIBLE"
    assert result["topical_overlap"] >= OVERLAP_THRESHOLD


def test_real_but_irrelevant(mock_snapshot):
    context = "Sequential port scanning activity detected on the internal network."
    result = verify_technique("T1055", context)
    assert result["classification"] == "REAL_BUT_IRRELEVANT"
    assert result["topical_overlap"] < OVERLAP_THRESHOLD


# ---------------------------------------------------------------------------
# 3. End-to-end check_attack_grounding
# ---------------------------------------------------------------------------

def test_no_ids_in_answer(mock_snapshot):
    result = check_attack_grounding(
        answer="No technique identifiers are mentioned.",
        retrieved_docs=["Some context about network scanning."]
    )
    assert result["technique_ids"] == []
    assert result["flagged"] is False
    assert result["requires_review"] is False


def test_mixed_citations(mock_snapshot):
    answer = (
        "The behaviour is consistent with T1055 process injection. "
        "It also resembles T9999 (a made-up technique) and the old T1086."
    )
    retrieved = [
        "Adversaries may inject code into processes to evade defenses."
    ]
    result = check_attack_grounding(answer, retrieved)

    assert "T1055" in result["technique_ids"]
    assert "T9999" in result["technique_ids"]
    assert "T1086" in result["technique_ids"]

    classes = {v["technique_id"]: v["classification"] for v in result["verifications"]}
    assert classes["T1055"] == "REAL_AND_PLAUSIBLE"
    assert classes["T9999"] == "FABRICATED"
    assert classes["T1086"] == "REVOKED"

    assert result["flagged"] is True
    assert "T9999" in result["ungrounded"]
    assert "T1086" in result["ungrounded"]


def test_all_plausible(mock_snapshot):
    answer = "This matches T1055."
    retrieved = [
        "Code injection into a running process is a classic process injection technique."
    ]
    result = check_attack_grounding(answer, retrieved)
    assert result["ungrounded"] == []
    assert result["flagged"] is False
    # requires_review only when something is ungrounded
    assert result["requires_review"] is False
    
def test_verify_technique_normalizes_case(mock_snapshot):
    result = verify_technique("t1055", "process injection into a running process")
    assert result["technique_id"] == "T1055"
    assert result["classification"] != "FABRICATED"


# ---------------------------------------------------------------------------
# 4. Annotation helper
# ---------------------------------------------------------------------------

def test_annotate_tags_ungrounded_ids(mock_snapshot):
    answer = "Activity consistent with T9999 and T1055."
    verifications = [
        {"technique_id": "T9999", "classification": "FABRICATED"},
        {"technique_id": "T1055", "classification": "REAL_AND_PLAUSIBLE"},
    ]
    annotated = annotate_answer(answer, verifications)
    assert "T9999 [⚠ FABRICATED]" in annotated
    assert "T1055 [⚠" not in annotated  # plausible ones are left clean


def test_annotate_does_not_mutate_original():
    original = "Consistent with T9999."
    verifications = [{"technique_id": "T9999", "classification": "FABRICATED"}]
    annotate_answer(original, verifications)
    assert original == "Consistent with T9999."
    
def test_annotate_does_not_corrupt_subtechnique():
    from attack_grounding import annotate_answer

    text = "Activity involves T1055 and T1055.011."
    verifications = [
        {"technique_id": "T1055", "classification": "REAL_BUT_IRRELEVANT"},
        {"technique_id": "T1055.011", "classification": "FABRICATED"},
    ]
    out = annotate_answer(text, verifications)
    assert "T1055.011 [⚠ FABRICATED]" in out
    assert "T1055 [⚠ REAL_BUT_IRRELEVANT]" in out
    assert "T1055 [⚠ REAL_BUT_IRRELEVANT].011" not in out


# ---------------------------------------------------------------------------
# 5. Missing snapshot handling
# ---------------------------------------------------------------------------

def test_missing_snapshot_returns_unverified(monkeypatch):
    monkeypatch.setattr(
        "attack_grounding._load_attack_techniques",
        lambda snapshot_path=None: {}
    )
    result = verify_technique("T1055", "any context")
    assert result["classification"] == "UNVERIFIED"