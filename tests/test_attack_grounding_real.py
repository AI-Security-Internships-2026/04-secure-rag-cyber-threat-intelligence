"""
Real-data tests for the ATT&CK grounding checker.

Loads the actual slim snapshot and verifies behaviour against real technique IDs.
Also writes a summary of the results to:
    experiments/results/attack_grounding_real_results.json
    
Full-snapshot / larger evaluation tests.
Skipped when the local slim snapshot is absent (not committed).
Always-on logic tests live in test_attack_grounding_fixture.py.
Expand labeled eval toward ~100 samples under experiments/data/.

Run:
    pytest tests/test_attack_grounding_real.py -v -s
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest # type: ignore
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from attack_grounding import (
    extract_attack_ids,
    verify_technique,
    check_attack_grounding,
    annotate_answer,
    _load_attack_techniques,
    DEFAULT_SNAPSHOT_PATH,
    OVERLAP_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SNAPSHOT = Path(DEFAULT_SNAPSHOT_PATH)
RESULTS_DIR = Path("experiments") / "results"
RESULTS_FILE = RESULTS_DIR / "attack_grounding_real_results.json"

pytestmark = pytest.mark.skipif(
    not SNAPSHOT.exists(),
    reason=f"Real snapshot not found at {SNAPSHOT}. Run: python -m src.data.create_attack_snapshot",
)


@pytest.fixture(scope="module")
def real_techniques():
    return _load_attack_techniques()


# ---------------------------------------------------------------------------
# Collect results across tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def results_collector():
    """Accumulates real-data observations so we can write them at the end."""
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "snapshot_path": str(SNAPSHOT),
        "overlap_threshold": OVERLAP_THRESHOLD,
        "snapshot_technique_count": None,
        "checks": [],
    }
    yield data

    # Write results after all tests in this module have finished
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n[results] Saved real-data grounding results → {RESULTS_FILE}")


# ---------------------------------------------------------------------------
# Sanity checks on the real dataset
# ---------------------------------------------------------------------------

def test_snapshot_loads_and_has_expected_size(real_techniques, results_collector):
    count = len(real_techniques)
    results_collector["snapshot_technique_count"] = count
    assert count > 700, f"Expected >700 techniques, got {count}"
    assert "T1055" in real_techniques
    assert real_techniques["T1055"]["name"] is not None


def test_revoked_field_is_boolean(real_techniques):
    sample = next(iter(real_techniques.values()))
    assert isinstance(sample["revoked"], bool)


# ---------------------------------------------------------------------------
# Existence checks
# ---------------------------------------------------------------------------

def test_real_technique_is_not_fabricated(real_techniques, results_collector):
    result = verify_technique("T1055", "dummy context about process injection")
    results_collector["checks"].append({
        "test": "real_technique_is_not_fabricated",
        "technique_id": "T1055",
        "classification": result["classification"],
        "name": result["name"],
        "topical_overlap": result["topical_overlap"],
    })
    assert result["classification"] != "FABRICATED"
    assert result["name"] is not None


def test_completely_fake_id_is_fabricated(real_techniques, results_collector):
    result = verify_technique("T9999", "any context")
    results_collector["checks"].append({
        "test": "completely_fake_id_is_fabricated",
        "technique_id": "T9999",
        "classification": result["classification"],
        "name": result["name"],
        "topical_overlap": result["topical_overlap"],
    })
    assert result["classification"] == "FABRICATED"
    assert result["name"] is None


def test_another_fake_id(real_techniques, results_collector):
    result = verify_technique("T1234.999", "any context")
    results_collector["checks"].append({
        "test": "another_fake_id",
        "technique_id": "T1234.999",
        "classification": result["classification"],
    })
    assert result["classification"] == "FABRICATED"


# ---------------------------------------------------------------------------
# Relevance checks with real descriptions
# ---------------------------------------------------------------------------

def test_t1055_with_matching_context(real_techniques, results_collector):
    context = (
        "The malware injects code into a running process in order to "
        "evade process-based defenses and execute arbitrary payloads."
    )
    result = verify_technique("T1055", context)
    results_collector["checks"].append({
        "test": "t1055_with_matching_context",
        "technique_id": "T1055",
        "context_type": "matching",
        "classification": result["classification"],
        "topical_overlap": result["topical_overlap"],
        "name": result["name"],
    })
    print(f"T1055 overlap (matching context): {result['topical_overlap']}")
    assert result["classification"] in ("REAL_AND_PLAUSIBLE", "REAL_BUT_IRRELEVANT")


def test_t1055_with_unrelated_context(real_techniques, results_collector):
    context = (
        "Sequential port scanning was observed across multiple internal hosts. "
        "No process or memory activity was recorded."
    )
    result = verify_technique("T1055", context)
    results_collector["checks"].append({
        "test": "t1055_with_unrelated_context",
        "technique_id": "T1055",
        "context_type": "unrelated",
        "classification": result["classification"],
        "topical_overlap": result["topical_overlap"],
        "name": result["name"],
    })
    print(f"T1055 overlap (unrelated context): {result['topical_overlap']}")
    assert result["classification"] == "REAL_BUT_IRRELEVANT"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def test_end_to_end_mixed_real_and_fake(real_techniques, results_collector):
    answer = (
        "The observed behaviour is consistent with T1055 (Process Injection). "
        "It also shows signs of T9999, which does not exist, "
        "and possibly the older T1086."
    )
    retrieved_docs = [
        "Adversaries may inject code into processes to evade defenses "
        "and potentially elevate privileges. Process injection is common."
    ]

    result = check_attack_grounding(answer, retrieved_docs)

    results_collector["checks"].append({
        "test": "end_to_end_mixed_real_and_fake",
        "technique_ids": result["technique_ids"],
        "verifications": result["verifications"],
        "ungrounded": result["ungrounded"],
        "flagged": result["flagged"],
        "requires_review": result["requires_review"],
    })

    assert "T1055" in result["technique_ids"]
    assert "T9999" in result["technique_ids"]

    classes = {v["technique_id"]: v["classification"] for v in result["verifications"]}
    assert classes["T9999"] == "FABRICATED"
    assert classes["T1055"] in ("REAL_AND_PLAUSIBLE", "REAL_BUT_IRRELEVANT", "REVOKED")
    assert result["flagged"] is True
    assert "T9999" in result["ungrounded"]


def test_annotation_with_real_result(real_techniques, results_collector):
    answer = "Activity maps to T1055 and the fake T9999."
    result = check_attack_grounding(
        answer,
        ["Process injection into running processes was detected."]
    )
    annotated = annotate_answer(answer, result["verifications"])

    results_collector["checks"].append({
        "test": "annotation_with_real_result",
        "original_answer": answer,
        "annotated_answer": annotated,
        "verifications": result["verifications"],
    })

    assert "T9999 [⚠ FABRICATED]" in annotated