#!/usr/bin/env python
# -*- encoding utf-8 -*-

import sys
import atexit
import cli.daemon
import humanize

from sqlalchemy.sql.expression import desc
from time import time
from flask import Flask, render_template, url_for, request, redirect, jsonify

from anchorbot import DBPATH
from datamodel import get_session_from_new_engine, Source, Article, Keyword

_host = "0.0.0.0"
_port = 8000
flask_app = Flask(__name__)


def show(mode, content, data=''):
    return render_template(
            "layout.html",
            style=url_for("static", filename="default.css"),
            mode=mode,
            content=content,
            data=data
        )


@flask_app.route("/")
@flask_app.route("/gallery")
@flask_app.route("/gallery/offset/<offset>")
def gallery(offset=0, number=5*3, since=259200):
    offset, number, since = map(int, [offset, number, since])
    radius = 3
    s = get_session_from_new_engine(DBPATH)
    articles = list(s.query(Article).\
            join(Article.keywords).\
            filter(Article.timesread == 0).\
            filter(Article.skipcount <= 5).\
            order_by(desc(Article.date)).\
            group_by(Article.title).\
            offset(offset * number * radius).\
            limit(number * radius))
    articles = sort_articles(articles, number)
    for art in articles: 
        art.skipped(time())
        s.merge(art)
    content = render_template(
            "gallery.html",
            style=url_for("static", filename="default.css"),
            articles=[art.dictionary() for art in articles],
            new_offset=offset+1
        )
    s.commit()
    s.close()
    return content

@flask_app.route("/hate/keyword/by/id/<keyword_id>")
def hate_key(keyword_id):
    return change_key(-1, keyword_id)


@flask_app.route("/feed/<url>")
@flask_app.route("/feed/id/<fid>")
def read_feed(fid=None, url=None):
    s = get_session_from_new_engine(DBPATH)
    if url:
        arts = s.query(Article).join(Article.source)
        arts = arts.filter(Source.link.contains(url)).order_by(Article.date)
        arts = arts.all()
    else:
        arts = s.query(Article).join(Article.source)
        arts = arts.filter(Source.ID == fid).order_by(desc(Article.date)).all()
    content = show("feed", arts)
    s.close()
    return content


@flask_app.route("/like/keyword/by/id/<keyword_id>")
def like_keyword(keyword_id):
    return change_key(1, keyword_id)


@flask_app.route("/list/feeds")
def get_feeds():
    s = get_session_from_new_engine(DBPATH)
    sources = s.query(Source).order_by(Source.title).all()
    content = render_template("feeds.html", sources=sources)
    s.close()
    return content


@flask_app.route("/json/select/<query>")
def selectSQL(query):
    s = get_session_from_new_engine(DBPATH)
    items = s.execute("SELECT %s" % query)
    s.close()
    return jsonify(items)


@flask_app.route("/list/keywords")
@flask_app.route("/list/keywords/<limit>")
def get_keywords(limit=30):
    s = get_session_from_new_engine(DBPATH)
    keywords = s.query(Keyword).\
            order_by(desc(Keyword.clickcount)).\
            limit(limit)
    content = render_template("keywords.html", keywords=keywords)
    s.close()
    return content


@flask_app.route("/hate/article/by/id/<article_id>")
def skip(article_id):
    if not article_id:
        return "0"
    result = "1"
    s = get_session_from_new_engine(DBPATH)
    art = s.query(Article).filter(Article.ID == article_id).first()
    art.skipcount += 1
    s.merge(art)
    s.commit()
    s.close()
    return "1"


@flask_app.route("/json/all/articles/by/keyword/<key>")
@flask_app.route("/json/all/articles/by/keyword/<key>/<top>")
@flask_app.route("/json/all/articles/by/keyword/<key>/<top>/<number>")
@flask_app.route("/json/all/articles/by/keyword/<key>/<top>/<number>/<since>")
def all_articles(key, top=0, number=5, since=259200):
    kid, top, number, since = map(int, [key, top, number, since])
    s = get_session_from_new_engine(DBPATH)
    articles = list(s.query(Article).\
            join(Article.keywords).\
            filter(Keyword.ID == kid).\
            order_by(desc(Article.date)).\
            group_by(Article.link).\
            offset(top * number).limit(number))
    content = jsonify(articles=[art.dictionary() for art in articles])
    s.close()
    return content


@flask_app.route("/json/latest/articles/by/keyword/<key>")
@flask_app.route("/json/latest/articles/by/keyword/<key>/<top>")
@flask_app.route("/json/latest/articles/by/keyword/<key>/<top>/<number>")
@flask_app.route("/json/latest/articles/by/keyword/<key>/<top>/<number>/<since>")
def articles(key, top=0, number=5, since=259200):
    kid, top, number, since = map(int, [key, top, number, since])
    s = get_session_from_new_engine(DBPATH)
    articles = list(s.query(Article).\
            filter(Article.timesread == 0).\
            join(Article.keywords).\
            filter(Keyword.ID == kid).\
            order_by(desc(Article.date)).\
            group_by(Article.link).\
            offset(top * number).\
            limit(number)
            )
    for art in articles:
        art.finished(time())
        s.merge(art)
    s.commit()
    content = jsonify(articles=[art.dictionary() for art in articles])
    s.close()
    return content


@flask_app.route("/json/top/keywords/<top>")
@flask_app.route("/json/top/keywords/<top>/<number>")
@flask_app.route("/json/top/keywords/<top>/<number>/<since>")
def top_keywords(top, number=5, since=259200):
    top, number, since = map(int, [top, number, since])
    s = get_session_from_new_engine(DBPATH)
    keywords = list(
            s.query(Keyword).\
            join(Article.keywords).\
            filter(Article.timesread == 0).\
            # filter(Article.date > time() - since).\
            group_by(Keyword.ID).\
            order_by(desc(Keyword.clickcount)).\
            offset(top * number).\
            limit(number)
            )
    content = jsonify(keywords=[kw.dictionary() for kw in keywords])
    s.close()
    return content


@flask_app.route("/json/top/articles/<top>")
@flask_app.route("/json/top/articles/<top>/<number>")
@flask_app.route("/json/top/articles/<top>/<number>/<since>")
def top_articles(top=0, number=5, since=259200):
    top, number, since = map(int, [top, number, since])
    radius = 3
    s = get_session_from_new_engine(DBPATH)
    articles = list(s.query(Article).\
            join(Article.keywords).\
            # filter(Article.timesread == 0).\
            # order_by(desc(Keyword.clickcount)).\
            order_by(desc(Article.date)).\
            group_by(Article.title).\
            offset(top * number * radius).\
            limit(number * radius))
    content = jsonify(articles=[art.dictionary() for art in sort_articles(articles, number)])
    s.close()
    return content

def sort_articles(articles, number=5):
    def sum_keyword_stats(art):
        points = art.date * 10 ** -10
        points -= 9*abs(art.timesread)
        points -= 3*abs(art.skipcount)
        for keyword in art.keywords:
            points += keyword.clickcount
            points -= 1
        return points
    if len(articles) == 0: print "empty list"
    return sorted(articles, key=sum_keyword_stats, reverse=True)[:number]

@flask_app.route("/json/top/articles/by/keyword/<key>")
@flask_app.route("/json/top/articles/by/keyword/<key>/<top>")
@flask_app.route("/json/top/articles/by/keyword/<key>/<top>/<number>")
@flask_app.route("/json/top/articles/by/keyword/<key>/<top>/<number>/<since>")
def top_articles_by_keyword(key, top=0, number=5, since=259200):
    kid, top, number, since = map(int, [key, top, number, since])
    s = get_session_from_new_engine(DBPATH)
    articles = list(s.query(Article).\
            filter(Article.timesread == 0).\
            join(Article.keywords).\
            filter(Keyword.ID == kid).\
            order_by(desc(Article.date)).\
            group_by(Article.link).\
            offset(top * number).limit(number))
    content = jsonify(articles=[art.dictionary() for art in articles])
    s.close()
    return content


@flask_app.route("/key/<keyword>")
def keyword(keyword):
    if keyword:
        keyword = keyword.split("+")[0]
        s = get_session_from_new_engine(DBPATH)
        kw = s.query(Keyword).\
                filter(Keyword.word == keyword).\
                first()
        content = show("key", [], data=kw)
        s.close()
        return content


@flask_app.route("/read/<aid>")
@flask_app.route("/read/<aid>/because/of/<kid>")
def read_article(aid=None, kid=None):
    if kid: like_keyword(kid)
    articles = list()
    more_articles = list()
    aids = map(int, aid.split("+"))
    if aids:
        s = get_session_from_new_engine(DBPATH)
        for aid in aids:
            art = s.query(Article).filter(Article.ID == aid).first()
            art.finished(time())
            s.merge(art)
            s.commit()
            articles.append(art)
    if kid:
        more_articles = list(s.query(Article).\
                # filter(Article.timesread == 0).\
                join(Article.keywords).\
                filter(Keyword.ID == kid).\
                filter(Article.date > articles[0].date).\
                order_by(desc(Article.date)).\
                group_by(Article.link).\
                limit(5))
        more_articles += list(s.query(Article).\
                # filter(Article.timesread == 0).\
                join(Article.keywords).\
                filter(Keyword.ID == kid).\
                filter(Article.date < articles[0].date).\
                order_by(desc(Article.date)).\
                group_by(Article.link).\
                limit(5))
    content = render_template(
            "read.html",
            style=url_for("static", filename="default.css"),
            articles=articles,
            more_articles=[art for art in more_articles if art.ID not in aids]
        )
    s.close()
    return content


@flask_app.route("/redirect/<aid>")
def redirect_source(aid=None, url=None):
    s = get_session_from_new_engine(DBPATH)
    art = s.query(Article).filter(Article.ID == aid).one()
    url = art.link
    s.close()
    return redirect(url)


@flask_app.route("/quit")
def shutdown():
    try:
        request.environ.get("werkzeug.server.shutdown")()
    except Exception, e:
        print str(e)
    return "Bye"


def change_key(change, keyword_id=None, keyword=None):
    s = get_session_from_new_engine(DBPATH)
    if keyword and not keyword_id:
        kw = s.query(Keyword).filter(Keyword.word == keyword).first()
    else:
        kw = s.query(Keyword).filter(Keyword.ID == keyword_id).first()
    kw.clickcount += change
    s.merge(kw)
    s.commit()
    s.close()
    return jsonify({"change": change, "kid": keyword_id})

@cli.daemon.DaemonizingApp
def server(cli_app):
    atexit.register(shutdown)
    if cli_app.params.daemonize:
        cli_app.log.info("About to daemonize")
        cli_app.daemonize()
    host, port = cli_app.params.hostport.split(":")
    flask_app.run(host=host, port=int(port),
            debug=cli_app.params.flaskdebug,
            use_reloader=True)

server.add_param("-hp", "--hostport", help="set host:port url", default="0.0.0.0:8000")
server.add_param("-fd", "--flaskdebug", help="set debugflag for flask", default="0.0.0.0:8000")
server.add_param("-r", "--reloader", help="use reloader", default=False)

if __name__ == "__main__":
    server.run()
