import re

# Patterns to scan in LLM output — last line of defence
LEAK_PATTERNS = {
    "IP_ADDRESS": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "FILE_HASH_MD5": r'\b[a-fA-F0-9]{32}\b',
    "FILE_HASH_SHA256": r'\b[a-fA-F0-9]{64}\b',
    "CVE": r'CVE-\d{4}-\d{4,7}',
    "EMAIL": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
}

# Safe values that should never be redacted even if they match patterns
WHITELIST = [
    "attack.mitre.org",
    "mitre.org",
    "github.com",
    "microsoft.com",
]

def scan_output(answer: str) -> tuple[str, list, bool]:
    """
    Scans LLM generated answer for sensitive patterns.
    Redacts anything found.
    Returns cleaned answer, list of what was found, and whether anything leaked.
    """
    cleaned = answer
    found = []
    leaked = False

    for label, pattern in LEAK_PATTERNS.items():
        matches = re.findall(pattern, cleaned)

        # Filter out whitelisted values
        matches = [m for m in matches if not any(safe in m for safe in WHITELIST)]

        if matches:
            leaked = True
            for match in matches:
                cleaned = cleaned.replace(match, f"[{label} REDACTED]")
            found.append(f"{label}: {matches}")

    return cleaned, found, leaked


# Test
if __name__ == "__main__":
    test_answer = """
    The malware communicates with C2 server at 192.168.1.45.
    The file hash is a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4.
    Contact john.smith@company.com for more details.
    Reference: attack.mitre.org
    Exploits CVE-2021-44228.
    """

    cleaned, found, leaked = scan_output(test_answer)
    print("Original:")
    print(test_answer)
    print("\nCleaned:")
    print(cleaned)
    print("\nFound:")
    for item in found:
        print(f"  - {item}")
    print(f"\nLeaked: {leaked}")