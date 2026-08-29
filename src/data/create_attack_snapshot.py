"""
One-time (or periodic) script that converts the full MITRE ATT&CK STIX
bundle into a slim technique-ID lookup used by the output grounding check.

Why this exists:
- The full STIX file (data/mitre_attack.json) is large and contains many
  object types we do not need at verification time.
- The grounding checker only needs: technique ID → name, description,
  revoked/deprecated flag, and official URL.
- Loading a small dict is fast and has zero network dependency.

Usage:
    python -m src.data.create_attack_snapshot
    python -m src.data.create_attack_snapshot --input data/mitre_attack.json
    python -m src.data.create_attack_snapshot --output data/mitre_attack/enterprise_attack_techniques.json
"""

import argparse
import json
import os
from datetime import datetime, timezone

DEFAULT_INPUT = os.path.join("data", "mitre_attack.json")
DEFAULT_OUTPUT = os.path.join("data", "mitre_attack", "enterprise_attack_techniques.json")


def build_snapshot(bundle: dict) -> dict:
    """
    Extract only attack-pattern objects and keep the four fields the
    grounding checker actually uses.
    """
    techniques = {}

    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue

        # Find the official MITRE technique ID (Txxxx or Txxxx.xxx)
        ref = next(
            (r for r in obj.get("external_references", [])
             if r.get("source_name") == "mitre-attack" and r.get("external_id")),
            None,
        )
        if ref is None:
            continue

        technique_id = ref["external_id"]

        # Treat both STIX "revoked" and ATT&CK "x_mitre_deprecated" as revoked
        is_revoked = bool(obj.get("revoked") or obj.get("x_mitre_deprecated"))

        techniques[technique_id] = {
            "name": obj.get("name"),
            "description": obj.get("description"),
            "revoked": is_revoked,
            "url": ref.get("url"),
        }

    return techniques


def main():
    parser = argparse.ArgumentParser(
        description="Create slim MITRE ATT&CK technique snapshot for grounding checks"
    )
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help="Path to the full STIX bundle")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help="Where to write the slim snapshot")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(
            f"Input STIX file not found: {args.input}\n"
            "Download it first or point --input to the correct location."
        )

    print(f"Reading full STIX bundle from {args.input} ...")
    with open(args.input, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    techniques = build_snapshot(bundle)

    snapshot = {
        "source": os.path.abspath(args.input),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "technique_count": len(techniques),
        "techniques": techniques,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    revoked_count = sum(1 for t in techniques.values() if t["revoked"])
    print(f"Wrote {len(techniques)} techniques "
          f"({revoked_count} revoked/deprecated) → {args.output}")


if __name__ == "__main__":
    main()