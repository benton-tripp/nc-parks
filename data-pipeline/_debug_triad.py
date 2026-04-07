"""Quick debug script to check triad detail page structure."""
import requests
from bs4 import BeautifulSoup

r = requests.get('https://nctriadoutdoors.com/places/volunteer-park/',
                 headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')

# Check for JSON-LD
for s in soup.find_all('script', type='application/ld+json'):
    txt = s.string[:500] if s.string else 'empty'
    print(f'JSON-LD: {txt}')

# Check for address / location in meta tags
for m in soup.find_all('meta'):
    name = m.get('name', '') + m.get('property', '')
    content = m.get('content', '')
    if any(k in name.lower() for k in ('geo', 'lat', 'lon', 'address', 'place', 'location')):
        print(f'META {name}={content}')

# Check for map iframes
for iframe in soup.find_all('iframe'):
    src = iframe.get('src', '')
    if 'map' in src.lower() or 'google' in src.lower():
        print(f'IFRAME: {src[:200]}')

# Check for geodir classes
for el in soup.select('[class*="geodir"], [class*="address"], [class*="location"], [class*="lat"]'):
    cls = el.get('class')
    txt = el.get_text(strip=True)[:100]
    print(f'GEO el: class={cls} text={txt}')

# Check for data attributes with coordinates
for el in soup.find_all(attrs=True):
    for attr, val in el.attrs.items():
        if isinstance(val, str) and any(k in attr.lower() for k in ('lat', 'lng', 'lon', 'coord')):
            print(f'DATA ATTR: {attr}={val} on <{el.name}>')

# Check categories/amenities
for a in soup.select('a[href*="/category/"]'):
    print(f'CATEGORY: {a.get_text(strip=True)} -> {a["href"]}')
