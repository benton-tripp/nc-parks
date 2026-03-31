"""Quick debug script to analyze dedup issues."""
import json
import math

parks = json.load(open("data/final/parks_latest.json"))

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# 1. John Chavis duplicates
print("=" * 60)
print("JOHN CHAVIS PARK ENTRIES:")
chavis = [p for p in parks if "chavis" in p["name"].lower()]
for p in chavis:
    amenities = ", ".join(k for k, v in p.get("amenities", {}).items() if v)
    print(f"  {p['name']}  src={p['source']}  ({p['latitude']:.5f}, {p['longitude']:.5f})")
    print(f"    amenities: {amenities or '(none)'}")
    print(f"    all_sources: {p.get('all_sources', 'N/A')}")
if len(chavis) >= 2:
    d = haversine_m(chavis[0]["latitude"], chavis[0]["longitude"],
                    chavis[1]["latitude"], chavis[1]["longitude"])
    print(f"  Distance between first two: {d:.0f}m")

# 2. Dog-park-only entries (no other amenities besides dog_park)
print("\n" + "=" * 60)
print("STANDALONE DOG PARKS (dog_park is only meaningful amenity):")
dog_only = [p for p in parks
            if p.get("amenities", {}).get("dog_park")
            and not p.get("amenities", {}).get("playground")
            and p.get("extras", {}).get("leisure") == "dog_park"]
print(f"  Count: {len(dog_only)}")
for p in dog_only[:10]:
    amenities = ", ".join(k for k, v in p.get("amenities", {}).items() if v)
    print(f"  {p['name']}  ({p['latitude']:.4f}, {p['longitude']:.4f})  amenities: {amenities}")

# 3. Private / non-public parks
print("\n" + "=" * 60)
print("PARKS WITH access != public / yes / None:")
private = [p for p in parks
           if p.get("extras", {}).get("access")
           and p["extras"]["access"] not in ("yes", "public", "permissive")]
print(f"  Count: {len(private)}")
for p in private[:15]:
    print(f"  {p['name']}  access={p['extras']['access']}  leisure={p['extras'].get('leisure')}")

# 4. Suspicious names (rooftop, private, etc.)
print("\n" + "=" * 60)
print("SUSPICIOUS NAMES:")
sus_words = ["rooftop", "private", "office", "corporate", "apartment", "condo", "hotel", "resort"]
suspicious = [p for p in parks if any(w in p["name"].lower() for w in sus_words)]
print(f"  Count: {len(suspicious)}")
for p in suspicious:
    print(f"  {p['name']}  src={p['source']}  leisure={p.get('extras', {}).get('leisure')}")

# 5. Stats on same-name parks that survived dedup
print("\n" + "=" * 60)
print("DUPLICATE NAMES THAT SURVIVED DEDUP:")
from collections import Counter
name_counts = Counter(p["name"].lower() for p in parks)
dupes = {name: count for name, count in name_counts.items() if count > 1}
sorted_dupes = sorted(dupes.items(), key=lambda x: -x[1])[:20]
for name, count in sorted_dupes:
    entries = [p for p in parks if p["name"].lower() == name]
    coords = [(p["latitude"], p["longitude"]) for p in entries]
    sources = [p["source"] for p in entries]
    # Max distance between any pair
    max_dist = 0
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            d = haversine_m(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            max_dist = max(max_dist, d)
    print(f"  {name} x{count}  sources={sources}  max_dist={max_dist:.0f}m")
