"""
privacy_filter_v3.py — Improved regex-based CTI redaction filter.

Improvements over privacy_filter.py (v1):
1. Validates real IP octets (0-255) instead of \d{1,3} which matches junk like 999.999.999.999
2. Catches DEFANGED indicators — the way analysts actually write IOCs in threat intel
   so they don't get auto-linked/clicked:
     - 192[.]168[.]1[.]45   /  192(.)168(.)1(.)45  /  192{.}168{.}1{.}45
     - evil[.]com  /  evil(dot)com  /  evil[dot]com
     - hxxp://evil.com  /  hxxps://evil.com
3. Adds SHA1 hash pattern (40 hex chars) — v1 only had MD5/SHA256
4. Domain regex is stricter: won't false-positive on code filenames (script.py),
   version strings, or decimal numbers, and requires a plausible TLD list
5. Whitelist matching is now exact-domain-or-subdomain, not naive substring
   (v1's `"attack.mitre.org" in match` would also whitelist "evil-attack.mitre.org.evil.com")

Reference sources used to build these patterns:
- ioc-finder (https://github.com/fhightower/ioc-finder) — defanging conventions
- iocextract (https://github.com/InQuest/python-iocextract) — defang regex approach
"""
import re

# Known safe domains (exact match or legit subdomain only)
WHITELIST_DOMAINS = [
    "attack.mitre.org",
    "mitre.org",
    "github.com",
    "microsoft.com",
    "nvd.nist.gov",
    "cve.mitre.org",
]

def _is_whitelisted(domain: str) -> bool:
    domain = domain.lower().strip(".")
    for safe in WHITELIST_DOMAINS:
        if domain == safe or domain.endswith("." + safe):
            return True
    return False

# One valid IP octet: 0-255
_OCTET = r'(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)'

# Separator between octets — normal dot, or common defanging styles
_SEP = r'(?:\.|\[\.\]|\(\.\)|\{\.\}|\s\.\s)'

IP_ADDRESS_PATTERN = rf'\b{_OCTET}{_SEP}{_OCTET}{_SEP}{_OCTET}{_SEP}{_OCTET}\b'

# Hashes — unambiguous by exact hex length
FILE_HASH_MD5_PATTERN = r'\b[a-fA-F0-9]{32}\b'
FILE_HASH_SHA1_PATTERN = r'\b[a-fA-F0-9]{40}\b'
FILE_HASH_SHA256_PATTERN = r'\b[a-fA-F0-9]{64}\b'

# Domains — plausible TLD allowlist to cut false positives on filenames/version strings.
# Supports normal dots and defanged separators (evil[.]com, evil(dot)com, evil[dot]com)
_DOMAIN_SEP = r'(?:\.|\[\.\]|\(\.\)|\{\.\}|\[dot\]|\(dot\)|\s\[dot\]\s)'
_TLDS = r'(?:com|net|org|io|gov|edu|mil|info|biz|co|ru|cn|xyz|top|club|online|site|tk)'
DOMAIN_PATTERN = rf'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{{0,61}}[a-zA-Z0-9])?{_DOMAIN_SEP}){{1,4}}{_TLDS}\b'

# Defanged protocol prefixes (hxxp / hxxps) — flag but do not require for domain match
DEFANGED_PROTOCOL_PATTERN = r'\bhxxps?://'

EMAIL_PATTERN = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.\-\[\]\(\)]+\.[a-zA-Z]{2,}\b'
CVE_PATTERN = r'CVE-\d{4}-\d{4,7}'

PATTERNS = {
    "IP_ADDRESS": IP_ADDRESS_PATTERN,
    "FILE_HASH_MD5": FILE_HASH_MD5_PATTERN,
    "FILE_HASH_SHA1": FILE_HASH_SHA1_PATTERN,
    "FILE_HASH_SHA256": FILE_HASH_SHA256_PATTERN,
    "DOMAIN": DOMAIN_PATTERN,
    "EMAIL": EMAIL_PATTERN,
    "CVE": CVE_PATTERN,
}

# Check Order: 
# Hashes must be checked before shorter patterns could partially consume them, and SHA256 before MD5 is irrelevant since lengths differ exactly.
# Check DOMAIN before EMAIL isn't required either since patterns don't overlap
# Structurally redacted longest-match-first per label group to avoid double-marking substrings.
_LABEL_ORDER = ["FILE_HASH_SHA256", "FILE_HASH_SHA1", "FILE_HASH_MD5",
                "EMAIL", "IP_ADDRESS", "DOMAIN", "CVE"]


def extract_entities(text: str) -> list:
    """Returns list of (label, value) without mutating text — for evaluation."""
    entities = []
    for label in _LABEL_ORDER:
        pattern = PATTERNS[label]
        matches = re.findall(pattern, text)
        if label == "DOMAIN":
            matches = [m for m in matches if not _is_whitelisted(m)]
        if label == "EMAIL":
            matches = [m for m in matches if "@" not in m or not _is_whitelisted(m.split("@")[-1])]
        for m in matches:
            entities.append((label, m))
    return entities


def redact_sensitive_info(text: str) -> tuple[str, list]:
    """
    Redacts sensitive CTI indicators from text using hardened regex.
    Returns (redacted_text, found) where found is a list of "LABEL: [values]" strings.
    """
    redacted = text
    found = []

    for label in _LABEL_ORDER:
        pattern = PATTERNS[label]
        matches = re.findall(pattern, redacted)

        if label == "DOMAIN":
            matches = [m for m in matches if not _is_whitelisted(m)]
        if label == "EMAIL":
            # don't redact emails at whitelisted domains (e.g. reports@mitre.org)
            matches = [m for m in matches if "@" not in m or not _is_whitelisted(m.split("@")[-1])]

        if matches:
            # de-dupe while preserving order, longest first so substrings don't
            # get double-processed
            seen = []
            for m in sorted(set(matches), key=len, reverse=True):
                seen.append(m)
            for match in seen:
                if match in redacted:
                    redacted = redacted.replace(match, f"[{label} REDACTED]")
            found.append(f"{label}: {seen}")

    return redacted, found


def is_prompt_injection(query: str) -> bool:
    injection_signatures = [
        "ignore previous instructions", "ignore all instructions", "disregard your",
        "reveal your system prompt", "forget everything", "you are now", "act as",
        "jailbreak", "exact ip address", "exact file hash", "give me the hash",
        "list all ip", "show me the ip", "repeat the exact", "word for word",
        "without any filtering", "without filtering", "reproduce the",
        "copy the document", "dump the context",
    ]
    query_lower = query.lower()
    return any(sig in query_lower for sig in injection_signatures)