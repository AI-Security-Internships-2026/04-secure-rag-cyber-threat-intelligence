"""
Fixture-based ATT&CK grounding tests (always-on).

Uses a small committed snapshot so CI/fresh clones do not skip.
Empirical FP/FN on 20→100 labeled samples lives under experiments/, not here.

Run: pytest tests/test_attack_grounding_fixture.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from attack_grounding import (  # noqa: E402
    annotate_answer,
    check_attack_grounding,
    verify_technique,
)

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "attack_techniques_fixture.json"


@pytest.fixture()
def fixture_snapshot(monkeypatch):
    assert FIXTURE_PATH.exists(), f"Missing fixture: {FIXTURE_PATH}"
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    techniques = data["techniques"]

    import attack_grounding as ag

    def _load(_snapshot_path=None):
        return techniques

    monkeypatch.setattr(ag, "_load_attack_techniques", _load)
    if hasattr(ag._load_attack_techniques, "cache_clear"):
        ag._load_attack_techniques.cache_clear()

    return techniques


def test_fixture_has_expected_ids(fixture_snapshot):
    assert set(fixture_snapshot) >= {"T1055", "T1055.011", "T1486", "T1086"}
    assert fixture_snapshot["T1086"]["revoked"] is True
    assert fixture_snapshot["T1055"]["revoked"] is False


def test_fabricated_id(fixture_snapshot):
    result = verify_technique("T9999", "any context about encryption or injection")
    assert result["classification"] == "FABRICATED"


def test_revoked_id(fixture_snapshot):
    result = verify_technique("T1086", "powershell scripts executed on host")
    assert result["classification"] == "REVOKED"
    assert result["name"] == "PowerShell"


def test_matching_context_is_plausible(fixture_snapshot):
    context = (
        "The malware injects code into a running process to evade "
        "process-based defenses and execute arbitrary payloads."
    )
    result = verify_technique("T1055", context)
    assert result["classification"] == "REAL_AND_PLAUSIBLE"
    assert result["topical_overlap"] is not None
    assert result["topical_overlap"] >= 0.40


def test_unrelated_context_is_irrelevant(fixture_snapshot):
    context = (
        "Sequential port scanning was observed across internal hosts. "
        "No process memory activity was recorded."
    )
    result = verify_technique("T1055", context)
    assert result["classification"] == "REAL_BUT_IRRELEVANT"
    assert result["topical_overlap"] is not None
    assert result["topical_overlap"] < 0.40


def test_matching_overlap_exceeds_unrelated_overlap(fixture_snapshot):
    matching = (
        "Adversaries inject code into processes to evade defenses "
        "and run arbitrary code inside another process."
    )
    unrelated = (
        "Phishing emails targeted finance users with fake login pages. "
        "No injection or process memory behavior was described."
    )
    m = verify_technique("T1055", matching)
    u = verify_technique("T1055", unrelated)
    assert m["topical_overlap"] is not None
    assert u["topical_overlap"] is not None
    assert m["topical_overlap"] > u["topical_overlap"]


def test_pipeline_flags_fabricated(fixture_snapshot):
    answer = "Primary technique is T1055; secondary claim uses T9999."
    retrieved = [
        "Adversaries may inject code into processes to evade process-based defenses."
    ]
    result = check_attack_grounding(answer, retrieved)
    classes = {v["technique_id"]: v["classification"] for v in result["verifications"]}
    assert classes["T9999"] == "FABRICATED"
    assert "T9999" in result["ungrounded"]
    assert result["flagged"] is True
    assert result["requires_review"] is True


def test_pipeline_all_plausible_no_review(fixture_snapshot):
    answer = "This matches T1055 process injection."
    retrieved = [
        "Code injection into a running process is a classic process injection "
        "technique used to evade process-based defenses."
    ]
    result = check_attack_grounding(answer, retrieved)
    assert result["ungrounded"] == []
    assert result["flagged"] is False
    assert result["requires_review"] is False


def test_pipeline_revoked_requires_review(fixture_snapshot):
    answer = "Legacy scripts used T1086."
    retrieved = ["powershell was used to run a remote payload"]
    result = check_attack_grounding(answer, retrieved)
    assert "T1086" in result["ungrounded"]
    assert result["requires_review"] is True


def test_annotate_parent_and_subtechnique(fixture_snapshot):
    text = "Activity involves T1055 and T1055.011 on the same host."
    verifications = [
        {"technique_id": "T1055", "classification": "REAL_BUT_IRRELEVANT"},
        {"technique_id": "T1055.011", "classification": "FABRICATED"},
    ]
    out = annotate_answer(text, verifications)
    assert "T1055.011 [⚠ FABRICATED]" in out
    assert "T1055 [⚠ REAL_BUT_IRRELEVANT]" in out
    assert "T1055 [⚠ REAL_BUT_IRRELEVANT].011" not in out