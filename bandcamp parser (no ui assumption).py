import urllib2  # html scraper
from bs4 import BeautifulSoup  # html parser
import re  # regex module
from collections import deque  # keep track of urls to scrape & parse
import heapq

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
    


SOURCE_URL = "https://mishkanyc.bandcamp.com/music"  #will become main program input
URL_QUEUE = deque([])
TAG_QUEUE = deque([])
OPENER = urllib2.build_opener()
OPENER.addheaders = [('User-agent', 'Mozilla/5.0')]
MAX_TAG_PAGES = 2
MAX_ALBUMS = 10
SOURCE_TAGS = []

def main():
    SOURCE_URL
    URL_QUEUE = deque([])
    TAG_QUEUE = deque([])
    SOURCE_TAGS = []
    pass

def make_music_page_url(url):
    """Converts band url into their music page."""
    if re.compile('/music').match(url) == None:
        return url + '/music'
    else:
        return url
        
def clean_url(url):
    """Converts album/track url to base band url."""
    cleaner = re.compile('(/(album|track|music|releases))(?![a-z])(/?)((.*)?)')
    cleaned_band_url = re.sub(cleaner, "", url)
    return cleaned_band_url
    
def make_soup(url):
    return BeautifulSoup(scrape_html(url))
        
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
            print "Scraping %s" % url
            html = response.read()
        else:
            print "Invalid URL: %s \n" % url
    except (urllib2.HTTPError, urllib2.URLError) as e:
        print "Failed to open {}: {}".format(url, e)
    return html

def parse_music_page(url, artist):
    """Find/add all albumes on band's music page to URL_QUEUE."""
    print "made it to parse_music_page"
    soup = make_soup(url)
    album_count = 0
    for album in soup.find_all('li', class_='square first-four'):
        for link in album.find_all('a'):
            print "found links in tag"
            if artist.same_artist(SOURCE_ARTIST) or album_count <= MAX_ALBUMS:
                album = link.get('href')
                clean = clean_url(url)
                print url, clean
                URL_QUEUE.append(clean + album)
                album_count += 1
            else: 
                print "done parsing music page"
                return
    for album in soup.find_all('li', class_='square '):
        for link in album.find_all('a'):
            print "found links in tag"
            if artist.same_artist(SOURCE_ARTIST) or album_count <= MAX_ALBUMS:
                album = link.get('href')
                clean = clean_url(url)
                print url, clean
                URL_QUEUE.append(clean + album)
                album_count += 1
            else: 
                print "done parsing music page"
                return

def get_album_tags(url, artist):
    """Find album's tags and add their urls and name to TAG_QUEUE."""
    soup = make_soup(url)
    for tag in soup.find_all('a', class_='tag'):
        tag_url = tag.get('href')
        pretag_url = re.compile('(.*)(.bandcamp.com/tag/)')
        tag_string = re.sub(pretag_url, "", tag_url).replace("-", " ") # get the tag from the tag url
        print tag_string + " --- " + tag_url
        if artist.same_artist(SESSION_ARTISTS.get_source_artist()):
            artist.update_tags(tag_string)
            if [tag_url, tag_string] not in TAG_QUEUE:
                SOURCE_TAGS.append(tag_string)
                TAG_QUEUE.append([tag_url, tag_string])
        elif tag_string in SOURCE_TAGS:
            artist.update_tags(tag_string)
   
def parse_tag_pages(url, tag):
    soup = make_soup(url)
    for album in soup.find_all("li", class_="item"):
        album_url = album.a.get("href")
        band_name = album.find(class_='itemsubtext').get_text()
        print band_name
        band_url = clean_url(album_url)
        SESSION_ARTISTS.add_artist(band_name, band_url)
    try:
        next_page = soup.find(class_='nextprev next').a.get('href')
        if int(next_page[-1:]) <= MAX_TAG_PAGES:
            parse_tag_pages(url[ :-7] + next_page, tag)
        else:
            print "Finished scraping %s: page limit reached." % tag 
    except AttributeError:
        print "Finished scraping %s: no more pages." % tag

def create_sql_db(db_name):
    print "Opening connection to %s." % (db_name + ".db")
    con = sqlite3.connect(db_name)
    sql = con.cursor()
    sql.execute("""CREATE TABLE IF NOT EXISTS artist_tags(
         artist TEXT,
         url TEXT,
         tag TEXT,
         count TEXT
    );""")
    return con, sql

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
         self.total_common_tag_count = 0
         self.unique_common_tag_count = 0
        
    def update_tags(self, tag):
        #updates tag count or adds new tag to dictionary
        self.total_common_tag_count += 1
        if tag not in self.tag_dictionary:
            self.unique_common_tag_count += 1
            self.tag_dictionary[tag] = 1
        else:
            self.tag_dictionary[tag] = self.tag_dictionary[tag] + 1
            
    def same_artist(self, ref_artist):
        #use unique band url to check if two artists are the same
        if ref_artist.get_url() == self.artist_url:
            return True
        else:
            return False
            
    def get_index(self):
        try:
            return self.total_common_tag_count/self.unique_common_tag_count
        except ZeroDivisionError:
            return 0
            
    def get_unique_tag_count(self):
        return self.unique_common_tag_count
        
    def get_common_tag_count(self):
        return self.total_common_tag_count
            
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
        if not self.artist_included(new_artist) and not new_artist.same_artist(self.source_artist):
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
        
class Timeout(Exception):
    pass


parse_music_page(SOURCE_URL, SOURCE_ARTIST)
SOURCE_NAME = get_source_artist_name(SOURCE_URL)
SESSION_ARTISTS = Session_Artists(SOURCE_NAME, SOURCE_URL)
SOURCE_ARTIST = SESSION_ARTISTS.get_source_artist()

con, sql = create_sql_db("JapBreak")


print "Source Artist: %s\n" % SOURCE_NAME

"""Get tags from all source artist's albums."""
print "Getting Source Artist tags.\n"
while len(URL_QUEUE) > 0 :
    try:
        url = URL_QUEUE.popleft()
        print url
        get_album_tags(url, SOURCE_ARTIST)
    except (urllib2.URLError, urllib2.HTTPError) as e:
        print e
    
"""Get artists from all source tag pages."""
print "Going through tag pages.\n"
while len(TAG_QUEUE) > 0:
    try:
        tag = TAG_QUEUE.popleft()
        tag_name = tag[1]
        tag_url = tag[0]
        parse_tag_pages(tag_url + '?page=1', tag_name)
    except (urllib2.URLError, urllib2.HTTPError) as e:
        print e
       
"""Go through SESSION_ARTISTS' music pages -> albums -> tags."""
print "Going through artist pages.\n"
print "SESSION_ARTISTS:", len(SESSION_ARTISTS.get_artist_list())
count = 0
error_count = 0
for artist in SESSION_ARTISTS.get_artist_list():
    print artist.get_name(), artist.get_url()
    try:
        parse_music_page(artist.get_url() + "/music", artist)
        while len(URL_QUEUE) > 0:
            count += 1
            url = URL_QUEUE.popleft()
            get_album_tags(url, artist)
            if ( count % 25 == 0):
                print count
    except (urllib2.URLError, urllib2.HTTPError, TypeError) as e:
        error_count += 1
        print e, error_count
        
print "\ndone looking at artists: %d errors\n" % error_count

print SESSION_ARTISTS.session_len()
print SESSION_ARTISTS.get_source_artist().get_tag_dictionary()
print SOURCE_TAGS

SESSION_HEAP = []
for artist in SESSION_ARTISTS.get_artist_list():
    tag_dict = artist.get_tag_dictionary()
    for tag in tag_dict:
        data = (artist.get_name(), artist.get_url(), tag, tag_dict[tag])
        sql.execute('INSERT INTO artist_tags VALUES (?,?,?,?)', data)
    heapq.heappush(SESSION_HEAP, ((100-artist.get_common_tag_count()), artist.get_name(), artist.get_url()))
for a in range(0,11):
    print heapq.heappop(SESSION_HEAP)
    
