import urllib2  # html scraper
from bs4 import BeautifulSoup  # html parser
import sys  # exit quits program prematurely in event of error
import sqlite3  # allows interaction with sql database (henceforth db)
import datetime  # strptime and strftime convert between date formats
import time  # sleep allows slight pause after each request to bandcamp servers
import numpy  # random.exponential determines variable sleep time between server
              #  requests (more human-like according to p4k master comment)
import itertools  #count function is convenient iterator
import re  # regex module

BAND_PAGE = "radiatorhospital.bandcamp.com"  #will become main program input
#MUSIC_PAGE_STRING = re.compile('/music')
if re.compile('/music').match(BAND_PAGE) != None:
    BAND_MUSIC_PAGE = BAND_PAGE + '/music'
else:
    pass

soup = BeautifulSoup(open("radiator hospital music page source.htm"))

# <title>Music | Radiator Hospital</title>
print('\n\nsoup.title\n\n')
print(soup.title)  

# title
print('\n\nsoup.title.name\n\n')
print(soup.title.name)

# Music | Radiator Hospital
print('\n\nsoup.title.string\n\n')
print(soup.title.string)

# head
print('\n\nsoup.title.parent.name\n\n')
print(soup.title.parent.name)

# 
print('\n\nsoup.p\n\n')
print(soup.p)

# 
print("\n\nsoup.p[class]\n\n")
print(soup.p['class'])

# 
print('\n\nsoup.a')
print(soup.a)

# 
print("\n\nsoup.find_all(a)\n\n")
print(soup.find_all('a'))

# 
print("\n\nsoup.find(id=link3)\n\n")
print(soup.find(id="link3"))

print(soup.prettify())
    
print('\nbreak\n')

#Finds all /album/ links on the band's music page
for tag in soup.find_all('li', class_='square '):
    for link in tag.find_all('a'):
        print(link.get('href'))