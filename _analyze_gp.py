import json
from collections import Counter

d = json.load(open('data/raw/google_places_20260406T153331.json'))
nc = [p for p in d if p.get('address') and ', NC ' in p['address']]

# Find non-park things that should be filtered
problematic_types = ['indoor_playground', 'amusement_center', 'amusement_park', 
                     'cemetery', 'restaurant', 'store', 'rv_park', 'museum', 'zoo', 'food']
for ptype in problematic_types:
    matches = [p for p in nc if ptype in p.get('extras',{}).get('google_types',[])]
    examples = [p['name'] for p in matches][:5]
    print(f'\n{ptype} ({len(matches)}):')
    for e in examples:
        print(f'  - {e}')

# Entries without park or playground type
no_park = [p for p in nc 
           if 'park' not in p.get('extras',{}).get('google_types',[]) 
           and 'playground' not in p.get('extras',{}).get('google_types',[])]
print(f'\nEntries without park or playground type: {len(no_park)}')
for p in no_park[:15]:
    types = ' | '.join(p.get('extras',{}).get('google_types',[]))
    print(f'  - {p["name"]} [{types}]')

# Name-based patterns that should be filtered
filter_words = ['trampoline', 'bounce', 'jump', 'laser', 'go-kart', 'go kart',
                'paintball', 'escape room', 'bowling', 'skating rink', 'ice rink',
                'golf course', 'country club', 'church', 'school']
print('\nName-based filter matches:')
for word in filter_words:
    matches = [p['name'] for p in nc if word.lower() in p['name'].lower()]
    if matches:
        print(f'\n  "{word}" ({len(matches)}):')
        for m in matches[:3]:
            print(f'    - {m}')

# Check entries with ratings info
rated = [p for p in nc if p.get('extras',{}).get('google_rating')]
print(f'\nWith ratings: {len(rated)} / {len(nc)}')
print(f'With rating count: {len([p for p in nc if p.get("extras",{}).get("google_rating_count")])}')
print(f'With URL: {len([p for p in nc if p.get("url")])}')
print(f'With coords: {len([p for p in nc if p.get("latitude") and p.get("longitude")])}')

# State/national parks
state_parks = [p for p in nc if 'state_park' in p.get('extras',{}).get('google_types',[])]
national_parks = [p for p in nc if 'national_park' in p.get('extras',{}).get('google_types',[])]
print(f'\nState parks: {len(state_parks)}')
for p in state_parks[:5]:
    print(f'  - {p["name"]}')
print(f'\nNational parks: {len(national_parks)}')
for p in national_parks[:5]:
    print(f'  - {p["name"]}')
