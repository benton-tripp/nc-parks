"""Debug triad - get JSON-LD and address from detail pages."""
import json, requests
from bs4 import BeautifulSoup

urls = [
    'https://nctriadoutdoors.com/places/volunteer-park/',
    'https://nctriadoutdoors.com/places/shaffner-park/',
    'https://nctriadoutdoors.com/places/allen-jay-park/',
]
for url in urls:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # JSON-LD
    for s in soup.find_all('script', type='application/ld+json'):
        if s.string and 'LocalBusiness' in s.string:
            data = json.loads(s.string)
            print(f"=== {data.get('name')} ===")
            print(f"  address: {data.get('address')}")
            print(f"  geo: {data.get('geo')}")
            print(f"  url: {data.get('url')}")
            print(f"  sameAs: {data.get('sameAs')}")
            print()
    
    # Categories / amenities from page
    cats = [a.get_text(strip=True) for a in soup.select('a[href*="/category/"]')]
    print(f"  categories: {cats}")
    print()
