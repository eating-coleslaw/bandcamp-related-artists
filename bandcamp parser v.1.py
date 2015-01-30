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
BAND_ALBUM_LINK_LIST = []
URL_QUEUE = deque([])
OPENER = urllib2.build_opener()
OPENER.addheaders = [('User-agent', 'Mozilla/5.0')]

def make_music_page_url(url):
    if re.compile('/music').match(url) == None:
        print 'added /music\n'        
        return url + '/music'
    else:
        return url
            
def check_url_protocol(url):
    if re.compile('http://').match(url) == None:
        url = 'http://' + url
        print 'added protocol\n'
        return url
    else:
        return url

def scrape_html(url):
    #Scrape html from a single url"
    #url = BAND_PAGE + href
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

#Finds all /album/ links on the band's music page & adds them to album list
def parse_music_page(soup):
    for tag in soup.find_all('li', class_='square '):
        for link in tag.find_all('a'):
            album = link.get('href')
            print(album)
            BAND_ALBUM_LINK_LIST.append(album)
            URL_QUEUE.append(check_url_protocol(BAND_PAGE) + album)

def get_album_tags(soup):
    for tag in soup.find_all('a', class_='tag'):
        tag_url = tag.get('href')
        print tag_url
            
def find_album_tags():
    pass

BAND_MUSIC_PAGE = make_music_page_url(BAND_PAGE)
BAND_MUSIC_PAGE = check_url_protocol(BAND_MUSIC_PAGE)
music_soup = BeautifulSoup(scrape_html(BAND_MUSIC_PAGE))
#music_soup = BeautifulSoup(open("radiator hospital music page source.htm"))
parse_music_page(music_soup)
album_soup = BeautifulSoup(scrape_html(URL_QUEUE.popleft()))
get_album_tags(album_soup)