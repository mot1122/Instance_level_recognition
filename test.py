import requests
from bs4 import BeautifulSoup

url = 'https://www.yomiuri.co.jp'
res = requests.get(url)
print(res.text)
