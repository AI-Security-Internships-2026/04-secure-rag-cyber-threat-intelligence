from privacy_filter_v3 import redact_sensitive_info


def scan_output(answer: str) -> tuple[str, list, bool]:
    """
    Scans LLM generated answer for sensitive patterns using the same
    hardened patterns as the main privacy filter (privacy_filter_v3).
    Redacts anything found.
    Returns cleaned answer, list of what was found, and whether anything leaked.
    """
    cleaned, found = redact_sensitive_info(answer)
    leaked = len(found) > 0
    return cleaned, found, leaked


# Test
if __name__ == "__main__":
    test_answer = """
    The malware communicates with C2 server at 192.168.1.45.
    Also seen defanged as 192[.]168[.]1[.]45 in some reports.
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