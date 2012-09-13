#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
This is the main class of AnchorBot, the feed reader that makes you read
the important news first.

For further reading, see README.md
"""

import feedparser
import argparse
import sys
import os
from logging import Logger, FileHandler, StreamHandler
from sqlalchemy.exc import IntegrityError, DatabaseError

import storage
from config import Config, HOME, TEMP, DBPATH, LockedException
from crawler import Crawler
from datamodel import (
        get_session, get_engine, Source, Article, Image, Keyword, Media)
from time import sleep, time
import atexit
import md5
import traceback

class Anchorbot(object):
    """
    The most main class

    It holds and calls initialization of:
    * singleton instance lock
    * configurations
    * feed downloads
    * start analysis of the downloaded feeds
    """

    def __init__(self, verbose=0, cache_only=False,
            update_call=lambda x: x):
        self.logger = Logger("root", level=verbose)
        self.logger.addHandler(FileHandler(filename=os.path.join(HOME,
            "anchorbot.log")))
        self.logger.addHandler(StreamHandler())
        self.log = self.logger.log
        self.info = self.logger.info
        self.error = self.logger.error
        self.debug = self.logger.debug
        self.fatal = self.logger.fatal
        self.critical = self.logger.critical

        try:
            # cache keeps files for 3 days
            self.debug("Init FileCacher dir=%s, days=%i" % (TEMP, 3))
            self.cache = storage.FileCacher(TEMP, 3)

            # prepare datamodel
            self.debug("Preparing database at %s" % DBPATH)
            self.db = get_engine(DBPATH)

            # prepare variables and lists,...
            self.debug("Preparing variables and lists")
            self.watched = None

            self.debug("Init crawler with cache")
            self.crawler = Crawler(self.cache)

        except IOError, e:
            self.error("IOError !", e.filename)

        # prepare lock, config, cache and variables
        # load config
        try:
            # Raises Exception if locked
            self.debug("Loading config from %s" % HOME)
            self.config = Config(HOME)
        except LockedException, e:
            self.error(e.msg)
            sys.exit(1)

    def run(self):
        self.running = True
        self.firsttimeout = 16
        self.timeouts, self.update = dict(), dict()
        self.debug("Running=%s, timeout=%s" % (self.running, self.timeouts))
        try:
            while self.running:
                t = time()

                # add urls
                for url in self.config.get_abos():
                    if url not in self.timeouts.keys():
                        self.timeouts[url] = self.firsttimeout
                        self.update[url] = 0

                # update all that have a small enough timeout
                check_these = [x[0] for x in self.update.items() if x[1] <= t]
                news = self.update_all(check_these)

                # update timeouts
                self.debug("Have news:", news)
                for url in check_these:
                    self.timeouts[url] *= .5 if url in news else 2
                    self.update[url] = t + self.timeouts[url]

                remaining = min(self.update.values()) - time()
                if remaining > 0:
                    self.debug("sleeping %i seconds" % (remaining))
                    sleep(remaining)
        except KeyboardInterrupt:
            self.debug("Keyboard interrupt")

    def __print_cache_and_exit(self):
        """ well, prints cache and exits """
        self.cache.pprint()
        self.shutdown()

    def shutdown(self, stuff=None):
        """Does a save shutdown"""
        # shutdown
        self.info("Shutting down...")
        self.running = False
        self.debug("Shutting down cache")
        self.cache.shutdown()
        self.debug("Shutting down config")
        self.config.shutdown()
        self.info("KTHXBYE!")

    def add_entry(self, entry, source):
        try:
            url = self.crawler.get_link(entry).encode("utf-8")
        except UnicodeError:
            url = str(self.crawler.get_link(entry))

        s = get_session(self.db)
        try:
            if s.query(Article).filter(Article.link == url).count():
                s.close()
                return 0
        except DatabaseError:
            self.error("Database error: %s" % url)
            s.close()
            return 0

        article, keywords, image_url, media = self.crawler.enrich(
                entry, source)
        s.add(article)
        s.commit()
        for kw in set(keywords):
            try:
                if s.query(Keyword).filter(Keyword.word == kw).count():
                    article.keywords.append(
                            s.query(Keyword).\
                                    filter(Keyword.word == kw).\
                                    first())
                else:
                    article.keywords.append(Keyword(kw))
                s.merge(article)
                s.flush()
            except IntegrityError, e:
                s.rollback()
                self.error("Keyword '%s' ignored: %s" % (kw, e))
        try:
            article.image = Image(image_url, self.cache[image_url])
            s.merge(article)
            s.flush
        except IntegrityError, e:
            s.rollback()
            article.image = s.query(Image).\
                    filter(Image.filename == image_url).\
                    first()
            s.merge(article)
        if (media is not None and len(media)) and\
                s.query(Media).filter(Media.filename == media).count():
            article.media = s.query(Media).\
                    filter(Media.filename == media).\
                    first()
        else:
            article.media = Media(media)
        s.merge(article)
        s.commit()
        s.close()
        return 1

    def download_feed(self, urls, callback=None):
        """Download procedure"""
        result = list()
        self.cache.get_all(urls, delete=True)
        sources = dict()
        hashes = dict()
        s = get_session(self.db)
        for source in s.query(Source).all():
            if source.link in sources.keys():
                s.delete(source)
                s.commit()
            else:
                sources[source.link] = source
                hashes[source.link] = source.quickhash
        s.close()
        for feedurl,i in zip(urls, range(len(urls))):
            old_quickhash = hashes[feedurl]
            new_quickhash = str(self.get_quickhash(feedurl))
            if old_quickhash == new_quickhash:
                self.info("[%i of %i] old %s" % (i+1, len(urls), feedurl))
            else:
                self.info("[%i of %i] new %s" % (i+1, len(urls), feedurl))
                source = sources[feedurl]
                hashes[feedurl] = source.quickhash = new_quickhash
                feed = None
                try:
                    feed = feedparser.parse(self.cache[feedurl])
                except Exception, e:
                    self.error("%s, %s" (e, feedurl,))
                if feed:
                    try:
                        title = source.title = feed["feed"]["title"]
                    except KeyError:
                        title = source.title = feedurl
                    s = get_session(self.db)
                    s.merge(source)
                    s.commit()
                    s.close()
                    new_articles = 0
                    for entry in feed["entries"]:
                        if not self.running:
                            break
                        new_articles += self.add_entry(entry, source)
                    if new_articles:
                        result.append(feedurl)
            if callback:
                callback(feedurl, title)

        return result

    def get_quickhash(self, feedurl):
        """Fast value for comparisons without hashing"""
        h = None
        tries = 4
        while tries and h is None:
            try:
                f = open(self.cache[feedurl], "r")
                h = md5.md5(f.read()).hexdigest()
                f.close()
            except IOError:
                tries -= 1
        return h

    def update_all(self, urls):
        """
        Puts all feeds into the download queue to be downloaded.
        Needs some DLers in downloaders list
        """
        s = get_session(self.db)
        for url in urls:
            if not self.running:
                break
            source = s.query(Source).filter(Source.link == url).first()
            if not source:
                self.info("New source: %s" % url)
                source = Source(url)
                s.add(source)
                try:
                    s.flush()
                except IntegrityError:
                    s.rollback()
                    self.error("Couldn't store source %s" % source)
                    continue
            s.commit()
        s.close()
        return self.download_feed(urls)

    def add_url(self, url):
        """Adds a feed url to the abos
        """
        try:
            self.config.add_abo(url)
            s = get_session(self.db)
            source = Source(url, None)
            s.add(source)
            s.commit()
            s.close()
        except Exception, e:
            self.error(str(e))
            traceback.print_exception(*e)

    def remove_url(self, url):
        """Removes a feed url from the abos
        """
        # TODO
        self.config.del_abo(url)


if __name__ == "__main__":
    app = argparse.ArgumentParser(description="AnchorBot")
    app.add_argument("-v", "--verbose", default=30, type=int)
    app.add_argument("-c", "--cacheonly", default=False, action="store_true")
    app.add_argument("-a", "--add", help="add new urls", default=None, type=str)
    args = app.parse_args()
    bot = Anchorbot(args.verbose, args.cacheonly)
    atexit.register(bot.shutdown)
    if args.add is not None:
        bot.add_url(args.add)
    bot.run()
