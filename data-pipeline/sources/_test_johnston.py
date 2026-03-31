"""Quick test to extract Johnston County park markers from listing page."""
import requests
import re

r = requests.get("https://www.johnstonnc.gov/parks/PlaygroundParks.cfm")
pattern = r'L\.marker\(\[([0-9.\-]+),\s*([0-9.\-]+)\]\)\.bindPopup\("&lt;b&gt;(.+?)&lt;/b&gt;'
markers = re.findall(pattern, r.text)

if not markers:
    # Try unescaped HTML
    pattern2 = r'L\.marker\(\[([0-9.\-]+),\s*([0-9.\-]+)\]\)\.bindPopup\("<b>(.+?)</b>'
    markers = re.findall(pattern2, r.text)

if not markers:
    # Try with single quotes
    pattern3 = r"L\.marker\(\[([0-9.\-]+),\s*([0-9.\-]+)\]\)\.bindPopup\('<b>(.+?)</b>"
    markers = re.findall(pattern3, r.text)

print(f"Found {len(markers)} markers")
for lat, lon, name in markers:
    print(f"  {name.strip()} | {lat}, {lon}")

# Also extract park links
links = re.findall(r'href="(https://www\.johnstonnc\.gov/parks/pcontent\.cfm\?id=\d+)"[^>]*>([^<]+)<', r.text)
print(f"\nFound {len(links)} park links")
for url, name in links:
    print(f"  {name.strip()} | {url}")
