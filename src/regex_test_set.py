"""
Labeled ground-truth test set for regex redaction accuracy.

Each case has:
  - text: sample CTI sentence
  - expected: list of (LABEL, exact_substring) that SHOULD be redacted
              (empty list = nothing should be redacted — tests false positives)

Design covers 4 categories on purpose:
  A. Plain, unambiguous indicators (should always be caught)
  B. Defanged indicators (the real-world way analysts write IOCs)
  C. Whitelisted / safe references (must NOT be redacted)
  D. False-positive traps (things that look like indicators but aren't)
"""

TEST_CASES = [
    # A. Plain indicators
    {"text": "Malware beacons to C2 server at 192.168.1.45 every 60 seconds.",
     "expected": [("IP_ADDRESS", "192.168.1.45")]},

    {"text": "The dropper hash is a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4.",
     "expected": [("FILE_HASH_MD5", "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4")]},

    {"text": "SHA1 of the payload: da39a3ee5e6b4b0d3255bfef95601890afd80709",
     "expected": [("FILE_HASH_SHA1", "da39a3ee5e6b4b0d3255bfef95601890afd80709")]},

    {"text": "Full SHA256 signature: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
     "expected": [("FILE_HASH_SHA256", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")]},

    {"text": "Domain used for phishing: malicious-site.com",
     "expected": [("DOMAIN", "malicious-site.com")]},

    {"text": "Contact analyst john.smith@company.com for more details.",
     "expected": [("EMAIL", "john.smith@company.com")]},

    {"text": "Exploits CVE-2021-44228 (Log4Shell) vulnerability.",
     "expected": [("CVE", "CVE-2021-44228")]},

    # B. Defanged indicators (real analyst writing style) 
    {"text": "C2 observed at 192[.]168[.]1[.]45 in the sandbox run.",
     "expected": [("IP_ADDRESS", "192[.]168[.]1[.]45")]},

    {"text": "Second beacon IP: 10(.)0(.)0(.)5 per the pcap.",
     "expected": [("IP_ADDRESS", "10(.)0(.)0(.)5")]},

    {"text": "Also seen: 172{.}16{.}0{.}9 as backup C2.",
     "expected": [("IP_ADDRESS", "172{.}16{.}0{.}9")]},

    {"text": "Payload downloaded from evil[.]com/dropper.exe",
     "expected": [("DOMAIN", "evil[.]com")]},

    {"text": "Registered attacker infra at bad-domain[.]net for phishing kits.",
     "expected": [("DOMAIN", "bad-domain[.]net")]},

    # C. Whitelisted / safe references (must NOT be redacted) 
    {"text": "Technique documented at attack.mitre.org/techniques/T1110.",
     "expected": []},

    {"text": "See advisory on nvd.nist.gov for the full CVSS score.",
     "expected": []},

    {"text": "Source code hosted at github.com/mitre/cti.",
     "expected": []},

    {"text": "Reference: cve.mitre.org for the canonical record.",
     "expected": []},

    {"text": "Patch notes published on microsoft.com/security-updates.",
     "expected": []},

    # D. False-positive traps
    {"text": "The tool is currently at version 1.2.3.4 in our internal build.",
     "expected": []},  # looks like an IP but is a version string — regex WILL still
                        # catch this since it's syntactically identical to an IP
                        # documented as a known limitation, not a bug

    {"text": "Malicious script saved as script.py on the compromised host.",
     "expected": []},  # .py is not in TLD allowlist — should NOT be flagged as domain

    {"text": "Config file located at settings.ini in the install directory.",
     "expected": []},

    {"text": "Ratio recorded was 0.998 during the benchmark run.",
     "expected": []},

    {"text": "Malformed address 999.999.999.999 appeared in a corrupted log line.",
     "expected": []},  # invalid IP — v1 (naive \d{1,3}) will false-positive here,
                        # v3 (octet-validated) should correctly ignore it

    {"text": "The archive is named backup.tar for the nightly job.",
     "expected": []},

    # Mixed real-world sentence (multiple entity types at once) 
    {"text": ("Adversaries use malware communicating with C2 server at 192.168.1.45. "
              "The malware hash is a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4. "
              "Contact analyst john.smith@company.com for more details. "
              "Exploits CVE-2021-44228 vulnerability. "
              "Domain used: malicious-site.com. "
              "Reference: attack.mitre.org"),
     "expected": [
         ("IP_ADDRESS", "192.168.1.45"),
         ("FILE_HASH_MD5", "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"),
         ("EMAIL", "john.smith@company.com"),
         ("CVE", "CVE-2021-44228"),
         ("DOMAIN", "malicious-site.com"),
     ]},

    {"text": ("Defanged report: C2 at 45[.]33[.]21[.]100, dropper served from "
              "phish-panel[.]ru, hash 5d41402abc4b2a76b9719d911017c592, "
              "vulnerable to CVE-2023-23397. Reference: attack.mitre.org."),
     "expected": [
         ("IP_ADDRESS", "45[.]33[.]21[.]100"),
         ("DOMAIN", "phish-panel[.]ru"),
         ("FILE_HASH_MD5", "5d41402abc4b2a76b9719d911017c592"),
         ("CVE", "CVE-2023-23397"),
     ]},

    # E. Ordering / substring-consumption regression cases ---
    # These prove the _LABEL_ORDER and longest-match-first logic in privacy_filter_v3.py.
    # If someone reorders labels or removes the longest-first sort, these should fail.

    {"text": "Analyst contact: john.smith@company.com regarding the incident.",
     "expected": [("EMAIL", "john.smith@company.com")]},
     # NOTE: extract_entities() will ALSO independently find ("DOMAIN", "company.com")
     # here since it scans fresh each time — that's expected and fine (see below).
     # The real regression this guards is in redact_sensitive_info(): EMAIL must be
     # replaced as a whole unit first, or the email gets mangled mid-string.

    {"text": "Payload beaconed to mail.evil.com, also seen contacting evil.com directly.",
     "expected": [("DOMAIN", "mail.evil.com"), ("DOMAIN", "evil.com")]},
     # Proves longest-match-first: "evil.com" must not be able to eat itself out of the
     # middle of "mail.evil.com" and leave "mail." dangling un-redacted.

    {"text": "Dropper hosted at hxxp://evil[.]com/payload.exe for delivery.",
     "expected": [("DEFANGED_URL", "hxxp://evil[.]com/payload.exe")]},
     # Proves DEFANGED_URL must run before DOMAIN in redact_sensitive_info(), or the
     # domain inside the URL gets partially consumed, leaving "hxxp://[DOMAIN...]" behind.
]