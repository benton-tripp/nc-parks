import json
import os 
import re

# Load latest Google Places data and print summary stats
data_dir = 'data/raw'
prefix = 'google_places_'
json_files = [f for f in os.listdir(data_dir) if f.startswith(prefix) and f.endswith('.json')]
latest = max(json_files, key=lambda f: re.search(r'google_places_(\d{8}T\d{6})\.json', f).group(1))
print("Latest Google Places file:", latest)
d = json.load(open(os.path.join(data_dir, latest))) 

# Basic stats
named = [p for p in d if p['name']!='Unknown'] 
rated = [p for p in d if p['extras'].get('google_rating')] 
with_url = [p for p in d if p.get('url')] 
print('Total:', len(d)) 
print('Named:', len(named)) 
print('With rating:', len(rated)) 
print('With URL:', len(with_url)) 
avg = sum(p['extras']['google_rating'] for p in rated)/len(rated) 
print('Avg rating:', round(avg,2)) 

# Top-rated parks
by_rev=sorted(rated, key=lambda p: p['extras'].get('google_rating_count',0), reverse=True) 
print('\nTop 25 by reviews:') 
for p in by_rev[:25]:
    print(' ', p['name'][:45], '-', p['extras']['google_rating'], 'stars,', p['extras']['google_rating_count'], 'reviews')
