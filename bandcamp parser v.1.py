import urllib2  # html scraper
from bs4 import BeautifulSoup  # html parser
import re  # regex module
from collections import deque  # keep track of urls to scrape & parse

import sys  # exit quits program prematurely in event of error
import sqlite3  # allows interaction with sql database (henceforth db)
import datetime  # strptime and strftime convert between date formats
import time  # sleep allows slight pause after each request to bandcamp servers
import numpy  # random.exponential determines variable sleep time between server
              #  requests (more human-like according to p4k master comment)
import itertools  #count function is convenient iterator


BAND_PAGE = "radiatorhospital.bandcamp.com"  #will become main program input
URL_QUEUE = deque([])
TAG_QUEUE = deque([])
OPENER = urllib2.build_opener()
OPENER.addheaders = [('User-agent', 'Mozilla/5.0')]

def make_music_page_url(url):
    if re.compile('/music').match(url) == None:
        return url + '/music'
    else:
        return url
            
def check_url_protocol(url):
    """Ensures a given url has the http:// protocl."""
    if re.compile('http://').match(url) == None:
        url = 'http://' + url
        return url
    else:
        return url

def scrape_html(url):
    """Scrapes html from a single url."""
    html = None
    try:
        response = OPENER.open(url)
        if response.code == 200:
            print "Scraping %s \n" % url
            html = response.read()
        else:
            print "Invalid URL: %s \n" % url
    except urllib2.HTTPError:
        print "Failed to open %s \n" % url
    return html

def parse_music_page(soup):
    """Find/add all albumes on band's music page to URL_QUEUE."""
    for tag in soup.find_all('li', class_='square '):
        for link in tag.find_all('a'):
            album = link.get('href')
            print(album)
            URL_QUEUE.append(check_url_protocol(BAND_PAGE) + album)

def get_album_tags(soup):
    """Find album's tags and add their urls to URL_QUEUE."""
    for tag in soup.find_all('a', class_='tag'):
        tag_url = tag.get('href')
        tag_string = tag_url[24: ].replace("-", " ") # get the tag from the tag url
        #print tag_string + " --- " + tag_url
        TAG_QUEUE.append([tag_url, tag_string])

def get_clean_band_url(url):
    """Convert album/track url to base band url."""
    cleaner = re.compile('(/([a-z]{5})/)(.*)$')
    cleaned_band_url = re.sub(cleaner, "", url)
    return cleaned_band_url
    
def parse_tag_pages(url):
    soup = BeautifulSoup(scrape_html(url))
    for album in soup.find_all("li", class_="item"):
        album_url = album.a.get("href")
        band_name = album.find(class_='itemsubtext').get_text()
        print band_name + " --- " + album_url
    if soup.find(class_='nextprev next').a != None:
        next_page = soup.find(class_='nextprev next').a.get('href')
        print next_page
        parse_tag_pages(url[ :-7] + next_page)
    else:
        print "\nFinished scraping tag."
    
    
class TagCount:
    """Used to create aggregate values in sql table."""
    def __init__(self):
        self.count = 0
        
    def step(self, value):
        self.count += value
        
    def finalize(self):
        return self.count

class Artist:
    def __init(self, name, url):
        artist_name = name
        artist_url = url
        tag_dictionary = {}
        
    def update_tags(self, tag):
        if tag not in tag_dictionary:
            tag_dictionary[tag] = 1
        else:
            tag_dictionary[tag] += 1
            
    def get_name(self):
        return artist_name
        
    def get_tag_dictionary(self):
        return tag_dictionary
        
    def get_tag_count(self, tag):
        return tag_dictionary[tag]

BAND_MUSIC_PAGE = check_url_protocol(make_music_page_url(BAND_PAGE))
music_soup = BeautifulSoup(scrape_html(BAND_MUSIC_PAGE))
parse_music_page(music_soup)
album_soup = BeautifulSoup(scrape_html(URL_QUEUE.popleft()))
get_album_tags(album_soup)
for lst in TAG_QUEUE:
    print lst
first_url = TAG_QUEUE.popleft()[0]
print first_url
#tag_soup = BeautifulSoup(scrape_html(first_url))
#print tag_soup.prettify()
parse_tag_pages(first_url + '?page=1')