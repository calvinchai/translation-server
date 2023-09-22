import requests 
from bs4 import BeautifulSoup as bs

response = requests.get('http://localhost:5000/')
visited = set()
soup = bs(response.text, 'html.parser')
for link in soup.findAll('a'):
    if link['href'] in visited:
        continue
    if not link['href'].startswith('http'):
        continue
    if link['href'][-3:] in ['jpg', 'png', 'gif', 'pdf']:
        continue
    print(link['href'])
    visited.update(link['href'])
    requests.get(link['href'])