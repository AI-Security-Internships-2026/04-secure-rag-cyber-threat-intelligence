import re

PATTERNS = {
    "IP_ADDRESS": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "FILE_HASH_MD5": r'\b[a-fA-F0-9]{32}\b',
    "FILE_HASH_SHA256": r'\b[a-fA-F0-9]{64}\b',
    "DOMAIN": r'\b(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|io|gov|edu|mil)\b',
    "EMAIL": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    "CVE": r'CVE-\d{4}-\d{4,7}',
}

WHITELIST_DOMAINS = [
    "attack.mitre.org",
    "mitre.org",
    "github.com",
    "microsoft.com",
    "nvd.nist.gov",
    "cve.mitre.org",
]

def extract_entities(text: str) -> list:
    """Returns list of (label, value) without mutating text — for evaluation."""
    entities = []
    for label, pattern in PATTERNS.items():
        matches = re.findall(pattern, text)
        if label == "DOMAIN":
            matches = [m for m in matches if m not in WHITELIST_DOMAINS]
        for m in matches:
            entities.append((label, m))
    return entities