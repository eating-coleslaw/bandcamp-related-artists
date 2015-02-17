import urllib2  # html scraper
from bs4 import BeautifulSoup  # html parser
import re  # regex module
from collections import deque  # keep track of urls to scrape & parse
import heapq  # used to sort artists once bandcamp parsing is finished 
import sqlite3  # allows interaction with sql database (henceforth db)
import time  # clock() measures run length. wait() used for request wait time
import numpy  # random.exponential determines variable sleep time between server

"""Script Sequence:
    1. go to music page of the source band
    2. get tags and tag counts from all albums on their music page
    3. for given tag, get band page for all artists listed
        4. repeat step 3 for all source artist tags
    5. for given session artist, get go through all albums counting tags
        6. repeat step 5 for all session artists
    7. move artist data into a heap sorted by total_common_tag_count (see Artist class)
    8. pop specified number off of the heap"""
    

#Global Variables
SOURCE_URL = "https://holybowlcut.bandcamp.com/music"  # "source" will always refer to aspects of this artist
database_name = "holybowlcut"
TAG_QUEUE = deque([])  # tag page urls from source artist albums added to this queue
URL_QUEUE = deque([])  # all other urls added to this queue; generally will be band page
OPENER = urllib2.build_opener()
OPENER.addheaders = [('User-agent', 'Mozilla/5.0')]
MAX_TAG_PAGES = 2  # how many pages of each tag to grab artists from
MAX_ALBUMS = 10  # max number of albums to parse when looking at artists' music pages
OUTPUT_AMOUNT = 10 # number of Artists to pop off of the heap after sorting
SOURCE_TAGS = []  # holds strings of all tags found for the source artist's albums
AVG_SECS_BETWEEN_REQUESTS = 3  # determines numpy exponential for server request wait time


def make_music_page_url(url):
    """Converts band url into their music page (a grid lists of all the artist's albums)."""
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
    """Takes a url and returns its BeautfiulSoup unless the attempt limit is reached."""
    attempts = 0
    while attempts < 3:
        try:
            soup = BeautifulSoup(scrape_html(url))
            return soup
        except:
            attempts += 1
            time.sleep(numpy.random.exponential(AVG_SECS_BETWEEN_REQUESTS, 1))  # pause between server requests
    print "Failed to scrape %s" % url
    return None  # lets soup parser functions know that the scraping/soupifting failed
        
def get_source_artist_name(url):
    """Gets name of the source artist off of its music page."""
    soup = make_soup(url)
    if soup != None:
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
    album_count = 0
    soup = make_soup(url)
    soup_albums = []  # will hold instances of 'square first-four' and 'square' classes, which represent albums in the html
    if soup != None:
        is_source_artist = artist.same_artist(SOURCE_ARTIST)  # if source artist music page, will want to look at all albums no matter what
        for album in soup.find_all('li', class_='square first-four'):
            soup_albums.append(album)
        for album in soup.find_all('li', class_='square '):
            soup_albums.append(album)
        for link in soup_albums:
            if is_source_artist or album_count <= MAX_ALBUMS:
                album_href = link.find('a').get('href')
                clean = clean_url(url)
                print url, clean
                URL_QUEUE.append(clean + album_href)
                album_count += 1
            else: 
                print "done parsing music page"
                return
        
def get_album_tags(url, artist):
    """Find album's tags and add their urls and name to TAG_QUEUE."""
    soup = make_soup(url)
    if soup != None:
        is_source_artist = artist.same_artist(SESSION_ARTISTS.get_source_artist())
        for tag in soup.find_all('a', class_='tag'):
            tag_url = tag.get('href')
            pretag_url = re.compile('(.*)(.bandcamp.com/tag/)')
            tag_string = re.sub(pretag_url, "", tag_url).replace("-", " ") # get the tag from the tag url
            #print tag_string + " --- " + tag_url
            if is_source_artist:
                artist.update_tags(tag_string)
                if [tag_url, tag_string] not in TAG_QUEUE:
                    SOURCE_TAGS.append(tag_string)
                    TAG_QUEUE.append([tag_url, tag_string])
            elif tag_string in SOURCE_TAGS:
                artist.update_tags(tag_string)
   
def parse_tag_pages(url, tag):
    soup = make_soup(url)
    tag_artists = []  # will hold artists found under current tag. serching this faster than defaulting to searching SESSION_ARTISTS
    tag_artists.append(SESSION_ARTISTS.get_source_artist().get_url())  # dont want the source artist being looked at again
    if soup != None:
        for album in soup.find_all("li", class_="item"):
            album_url = album.a.get("href")
            band_name = album.find(class_='itemsubtext').get_text()
            print band_name
            band_url = clean_url(album_url)
            if band_url not in tag_artists:  # artists likely to appear multiple times under same tag
                tag_artists.append(band_url)
                SESSION_ARTISTS.add_artist(band_name, band_url)
        try:
            next_page = soup.find(class_='nextprev next').a.get('href')
            if int(next_page[-1:]) <= MAX_TAG_PAGES:
                parse_tag_pages(url[ :-7] + next_page, tag) # last 7 characters are ?page=#
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

class Artist:
    """Instance of a bandcamp artist identified by unique name  +url."""
    def __init__(self, name, url):
         self.artist_name = name
         self.artist_url = url
         self.tag_dictionary = {}
         self.total_common_tag_count = 0  # total count of all source tag appearances
         self.unique_common_tag_count = 0  # unique tags shared with the source artist
        
    def update_tags(self, tag): # updates tag count or adds new tag to dictionary
        self.total_common_tag_count += 1
        if tag not in self.tag_dictionary:
            self.unique_common_tag_count += 1
            self.tag_dictionary[tag] = 1
        else:
            self.tag_dictionary[tag] = self.tag_dictionary[tag] + 1
            
    def same_artist(self, ref_artist):  #use unique band url to check if two artists are the same
        if ref_artist.get_url() == self.artist_url:
            return True
        else:
            return False
            
    def get_index(self):
            return self.total_common_tag_count/self.unique_common_tag_count
            
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
        
    def get_tag_count(self, tag):  # returns current count of the specified tag
        return  self.tag_dictionary[tag]
        
class Session_Artists:
    """List of all Artists created during runtime. Identified by the source Artist."""
    def __init__(self, name, url):
        self.source_artist = Artist(name, url)
        self.artist_list = []
        
    def set_source_artist(self, name, url):
        self.source_artist = Artist(name, url)
    
    def add_artist(self, name, url):  # if artist not alread in session, creats a new artist then appends it
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

"""MAIN SCRIPT START:"""
time.clock()  # set start time
con, sql = create_sql_db(database_name)

"""1. Get Source Artist's name and add albums from its music page to URL_QUEUE."""
SOURCE_NAME = get_source_artist_name(SOURCE_URL)
SESSION_ARTISTS = Session_Artists(SOURCE_NAME, SOURCE_URL)
SOURCE_ARTIST = SESSION_ARTISTS.get_source_artist()
parse_music_page(SOURCE_URL, SOURCE_ARTIST)
print "\nSource Artist: %s\n" % SOURCE_NAME

"""2. Get tags from all source artist's albums."""
print "Getting Source Artist tags.\n"
while len(URL_QUEUE) > 0 :
    try:
        url = URL_QUEUE.popleft()
        print url
        get_album_tags(url, SOURCE_ARTIST)
    except (urllib2.URLError, urllib2.HTTPError) as e:
        print e
    
"""3. Get artists from all source tag pages."""
print "Going through tag pages: %d pages.\n" % len(TAG_QUEUE)
while len(TAG_QUEUE) > 0:
    try:
        tag = TAG_QUEUE.popleft()
        tag_name = tag[1]
        tag_url = tag[0]
        parse_tag_pages(tag_url + '?page=1', tag_name)
    except (urllib2.URLError, urllib2.HTTPError) as e:
        print e
       
"""4. Go through SESSION_ARTISTS' music pages -> albums -> tags."""
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
        
print "\nDone looking at artists: %d errors\n" % error_count

print "Session Artist Count:", SESSION_ARTISTS.session_len()
for tag in SESSION_ARTISTS.get_source_artist().get_tag_dictionary():
    print tag, ":", SESSION_ARTISTS.get_source_artist().get_tag_dictionary()[tag]

"""5. Create a heap from SESSION_ARTISTS sorted by common tag count, then get top
10 matches. 100-# because heap pops smallest to largest."""
SESSION_HEAP = []
for artist in SESSION_ARTISTS.get_artist_list():
    tag_dict = artist.get_tag_dictionary()
    for tag in tag_dict:
        data = (artist.get_name(), artist.get_url(), tag, tag_dict[tag])
        sql.execute('INSERT INTO artist_tags VALUES (?,?,?,?)', data)
    heapq.heappush(SESSION_HEAP, ((100-artist.get_common_tag_count()), artist.get_name(), artist.get_url()))
for a in range(0,(OUTPUT_AMOUNT+1)):
    print heapq.heappop(SESSION_HEAP)
    
print "\nElapsed time:", time.clock(), "seconds"
    
