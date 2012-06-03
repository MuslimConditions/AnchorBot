AnchorBot
=========

![AnchorBot as seen in a Firefox with Pentadactyl Extension on Xubuntu 11.10 with Awesome WM](https://github.com/spazzpp2/AnchorBot/raw/master/screenshot.png)

It's a news feed reader with the attempt of making you read the most important
news first.


Features
--------
* gets pictures out of the RSS feeds and the page they're linking to
* analyzes feed entries for repeatations in microblogs or other feeds to merge and sort
* focus on readability
* locally hosted webinterface to run inside your browser

For more information, please read the [Wiki](http://github.com/spazzpp2/AnchorBot/wiki).


Installation
------------
Python >= 2.6 needed! No Apache.

*Ubuntu:*

    sudo setup.ubuntu.sh && ./anchorbot.linux

*all other:*

    setup.py install

*Windows:*

Tell me ;)

*⚠ Running it the first time may take some minutes even with a fast Internet
connection!*


Usage
-----
* To add rss/atom feeds (not implemented in web interface yet), append a line
with your feed-url to `~/.ancorbot/abos`.

    echo "yourfeedurl" >> ~/.anchorbot/abos

* Call `anchorbot.linux` to open your browser with anchorbot's front page.


Related Projects
----------------
* [Prismatic](http://www.getprismatic.com/)
* [Flipboard](http://flipboard.com/)
* [Hotot](https://code.google.com/p/hotot)
* [Google Reader](http://reader.google.com/)
* [Scrolldit](http://scrolldit.com/)
* [TweetMag](http://www.tweetmagapp.com/)
* [Starberryj.am](http://strawberryj.am/)
* [Vienna RSS](http://www.vienna-rss.org/)
* [Refynr](http://refynr.com/)
* [Summify](http://summify.com/)


*Version 1.0 beta*

*© spazzpp2 – Licensed under MIT License*

This project was once known as "Lyrebird" and is - as before - still a tribute
to the [bird that retweets](http://youtu.be/7XiQDgNUEMw) the terrifying
chainsaws that sew down it's rain forest.
