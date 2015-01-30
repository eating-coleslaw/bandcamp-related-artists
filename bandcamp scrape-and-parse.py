import urllib2  # html scraper
from bs4 import BeautifulSoup  # html parser
import sys  # exit quits program prematurely in event of error
import sqlite3  # allows interaction with sql database (henceforth db)
import datetime  # strptime and strftime convert between date formats
import time  # sleep allows slight pause after each request to bandcamp servers
import numpy  # random.exponential determines variable sleep time between server
              #  requests (more human-like according to p4k master comment)
import itertools  #count function is convenient iterator

# import signal - handles Timeout errors, in case scrape/parse take too long;
# only available on Unix OSs. find what it does and replace it

# global variables
BASE_URL = 'radiatorhospital.bandcamp.com/music'
OPENER = urllib2.build_opener()
OPENER.addheaders = [('User-agent', 'Mozilla/5.0')]  # claims web scraper isn't a bot
AVERAGE_SECONDS_BETWEEN_REQUESTS = 5  # respect tha servers
DATABASE_NAME = 'related-bandcamp-artists.db'  # must end in .db