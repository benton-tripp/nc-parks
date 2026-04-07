import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

from sources.google_places import fetch

parks = fetch()
print(f"\nTotal parks after filtering: {len(parks)}")

if parks:
    sample = parks[0]
    print(f"\nSample park:")
    print(f"  Name: {sample.get('name')}")
    print(f"  Address: {sample.get('address')}")
    print(f"  Rating: {sample.get('extras', {}).get('google_rating')}")
    print(f"  Rating count: {sample.get('extras', {}).get('google_rating_count')}")
    print(f"  Data date: {sample.get('extras', {}).get('google_data_date')}")
    print(f"  Extras keys: {list(sample.get('extras', {}).keys())}")

    # Stats
    rated = [p for p in parks if p.get("extras", {}).get("google_rating")]
    with_url = [p for p in parks if p.get("url")]
    with_coords = [p for p in parks if p.get("latitude") and p.get("longitude")]
    print(f"\n  With ratings: {len(rated)}")
    print(f"  With URL: {len(with_url)}")
    print(f"  With coords: {len(with_coords)}")
    
    if rated:
        avg = sum(p["extras"]["google_rating"] for p in rated) / len(rated)
        print(f"  Avg rating: {avg:.2f}")

    # Check a few filtered entries to validate
    print(f"\n  Last 5 park names:")
    for p in parks[-5:]:
        print(f"    - {p['name']}")
