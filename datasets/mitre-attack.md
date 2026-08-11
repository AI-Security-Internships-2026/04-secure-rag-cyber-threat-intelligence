## MITRE ATT&CK Enterprise Dataset

- **Source URL:** https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json
- **Licence:** Apache 2.0 — free for research and commercial use
- **Version / date downloaded:** 2026-06-24
- **Size:** approximately 70MB, 700+ attack technique objects
- **Format:** STIX 2.1 JSON bundle
- **Download command / script:**
```bash
  curl -o data/mitre_attack.json https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json
```
- **Preprocessing steps:**
  1. Filter objects by type `attack-pattern` to extract techniques
  2. Extract `name` and `description` fields for embedding
  3. Create a slim technique snapshot for the output grounding checker:
```bash
  python -m src.data.create_attack_snapshot
```
This produces data/mitre_attack/enterprise_attack_techniques.json (technique ID → name, description, revoked, url).
The generated file is not committed (see repository dataset policy).
- **Train / Val / Test split:** N/A — used as a knowledge base for retrieval
- **Notes:** Do not commit the raw JSON file. Download locally using the command above before running src/ingest.py. Do not commit the generated slim snapshot either.
Both must be created locally after cloning.