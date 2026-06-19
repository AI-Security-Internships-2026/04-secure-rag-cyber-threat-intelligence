import stix2

malware = stix2.Malware(
    name="Test Ransomware",
    description="A test malware object based on MITRE ATT&CK style threat intel",
    is_family=False
)

print("STIX2 working!")
print(malware.serialize(pretty=True))