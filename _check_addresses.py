import json
from collections import Counter

with open("data/final/parks_latest.json") as f:
    parks = json.load(f)

no_addr = [p for p in parks if not p.get("address")]
has_addr = [p for p in parks if p.get("address")]

print(f"Total: {len(parks)}")
print(f"With address: {len(has_addr)}")
print(f"Missing address: {len(no_addr)}")

print(f"\nBy source (missing):")
for src, c in Counter(p["source"] for p in no_addr).most_common():
    print(f"  {src}: {c}")

print(f"\nSample missing (first 10):")
for p in no_addr[:10]:
    print(f"  {p['name']} ({p['latitude']:.4f}, {p['longitude']:.4f}) [{p['source']}]")
