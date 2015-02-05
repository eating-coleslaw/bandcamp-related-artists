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


'''Script Sequence:
    1. go to music page of the source band
    2. get tags and tag counts from all albums on music page
    3. for given tag, get band page for all artists listed
        4. repeat step 3 for all reference band tags
    5. for given session artist, get go through all albums counting tags
        6. repeat step 5 for all session artists
    7. move information to database with (id, artist, tag, tag count)
    8. sort database based on tag count'''
    


SOURCE_URL = "radiatorhospital.bandcamp.com"  #will become main program input
URL_QUEUE = deque([])
TAG_QUEUE = deque([])
OPENER = urllib2.build_opener()
OPENER.addheaders = [('User-agent', 'Mozilla/5.0')]
MAX_TAG_PAGES = 3

def main():
    pass


def prepare_source_band_url(url):
    """Cleans the user-input source url and turns it into a music page url."""
    # check to ensure bandcamp.com link
    bandcamp_check = re.compile('(.*)(bandcamp\.com)(.*)$')
    if bandcamp_check.match(url) != None:
        clean_url = check_url_protocol(get_clean_band_url(url))
        return make_music_page_url(clean_url)
    else:
        print '%s is not a bandcamp.com URL.' % url
        return

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
        
def get_source_artist_name(url):
    """Gets name of the source artist off of its music page."""
    soup = make_soup(url)
    name = soup.find('p', id='band-name-location').find(class_='title').get_text()
    return name
    
    
def scrape_html(url):
    """Scrapes html from a single url."""
    html = None
    try:
        response = OPENER.open(url)
        if response.code == 200:
            print "\nScraping %s\n" % url
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
            URL_QUEUE.append(check_url_protocol(SOURCE_URL) + album)

def get_album_tags(soup, artist):
    """Find album's tags and add their urls and name to TAG_QUEUE."""
    for tag in soup.find_all('a', class_='tag'):
        tag_url = tag.get('href')
        tag_string = tag_url[24: ].replace("-", " ") # get the tag from the tag url
        #print tag_string + " --- " + tag_url
        artist.update_tags(tag_string)
        if artist.same_artist(SESSION_ARTISTS.get_source_artist()):
            if [tag_url, tag_string] not in TAG_QUEUE:
                TAG_QUEUE.append([tag_url, tag_string])

def get_clean_band_url(url):
    """Convert album/track url to base band url."""
    cleaner = re.compile('(/([a-z]{5})/)(.*)$')
    cleaned_band_url = re.sub(cleaner, "", url)
    return cleaned_band_url
    
def parse_tag_pages(url, tag):
    soup = make_soup(url)
    for album in soup.find_all("li", class_="item"):
        album_url = album.a.get("href")
        band_name = album.find(class_='itemsubtext').get_text()
        band_url = get_clean_band_url(album_url)
        SESSION_ARTISTS.add_artist(band_name, band_url)
        print band_name + " --- " + album_url
    #if soup.find(class_='nextprev next') != None:
    try:
        #if soup.find(class_='nextprev next').a != None:
        next_page = soup.find(class_='nextprev next').a.get('href')
        if int(next_page[-1:]) <= MAX_TAG_PAGES:
            print next_page
            parse_tag_pages(url[ :-7] + next_page, tag)
        else:
            print "\nFinished scraping %s: page limit reached.\n" % tag 
    except AttributeError: # else:
        print "\nFinished scraping %s: no more pages.\n" % tag
        
def make_soup(url):
    return BeautifulSoup(scrape_html(url))
    

class TagCount:
    """Used to create aggregate values in sql table."""
    def __init__(self):
        self.count = 0
        
    def step(self, value):
        self.count += value
        
    def finalize(self):
        return self.count

class Artist:
    def __init__(self, name, url):
         self.artist_name = name
         self.artist_url = url
         self.tag_dictionary = {}
        
    def update_tags(self, tag):
        #updates tag count or adds new tag to dictionary
        if tag not in self.tag_dictionary:
            self.tag_dictionary[tag] = 1
        else:
            self.tag_dictionary[tag] += 1
            
    def same_artist(self, ref_artist):
        #use unique band url to check if two artists are the same
        if ref_artist.get_url() == self.artist_url:
            return True
        else:
            return False
            
    def get_name(self):
        return  self.artist_name
        
    def get_url(self):
        return  self.artist_url
        
    def get_tag_dictionary(self):
        return  self.tag_dictionary
        
    def get_tag_count(self, tag):
        #returns current count of the specified tag
        return  self.tag_dictionary[tag]
        
class Session_Artists:
    def __init__(self, name, url):
        self.source_artist = Artist(name, url)
        self.artist_list = []
        
    def set_source_artist(self, name, url):
        self.source_artist = Artist(name, url)
    
    def add_artist(self, name, url):
        new_artist = Artist(name, url)
        if not self.artist_included(new_artist):
            self.artist_list.append(new_artist)
        
    def artist_included(self, new_artist):
        for artist in self.artist_list:
            if new_artist.same_artist(artist):
                return True
        return False           
                
    def get_artist_list(self):
        return self.artist_list
        
    def get_source_artist(self):
        return self.source_artist
        
    def session_len(self):
        return len(self.artist_list)
        
SOURCE_MUSIC_URL = prepare_source_band_url(SOURCE_URL)
music_soup = make_soup(SOURCE_MUSIC_URL)
parse_music_page(music_soup)

SOURCE_NAME = get_source_artist_name(SOURCE_MUSIC_URL)

SESSION_ARTISTS = Session_Artists(SOURCE_NAME, SOURCE_MUSIC_URL)

print SESSION_ARTISTS.get_source_artist().get_name()

album_soup = make_soup(URL_QUEUE.popleft())
get_album_tags(album_soup, SESSION_ARTISTS.get_source_artist())
while len(TAG_QUEUE) > 0:
    tag = TAG_QUEUE.popleft()
    tag_name = tag[1]
    tag_url = tag[0]
    #print first_url
    #tag_soup = BeautifulSoup(scrape_html(first_url))
    #print tag_soup.prettify()
    parse_tag_pages(tag_url + '?page=1', tag_name)

#for artist in SESSION_ARTISTS.get_artist_list():
#print artist.get_url()
print SESSION_ARTISTS.session_len()
        #print artist.get_name() + ' --- ' + artist.get_tag_dictionary()[tag]
