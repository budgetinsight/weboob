# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from urlparse import urlsplit, parse_qs

from weboob.tools.browser import BrokenPageError

from .index import PhpBBPage
from ..tools import parse_date


__all__ = ['Link', 'ForumPage', 'TopicPage']


class Link(object):
    (FORUM,
     TOPIC) = xrange(2)

    def __init__(self, type, url):
        self.type = type
        self.url = url
        self.title = u''
        self.date = None
        self.nb_messages = 0

class ForumPage(PhpBBPage):
    def iter_links(self):
        for li in self.parser.select(self.document.getroot(), 'ul.forums li.row'):
            title = li.cssselect('a.forumtitle')[0]
            link = Link(Link.FORUM, title.attrib['href'])
            link.title = title.text.strip()
            yield link

        for li in self.parser.select(self.document.getroot(), 'ul.topics li.row'):
            title = li.cssselect('a.topictitle')[0]
            link = Link(Link.TOPIC, title.attrib['href'])
            link.title = title.text.strip()
            for a in li.find('dl').find('dt').findall('a'):
                for text in (a.text, a.tail):
                    if text is None:
                        continue
                    try:
                        link.date = parse_date(text.strip(u'» \r\n'))
                    except ValueError:
                        continue
                    else:
                        break
            # it only lists number of answers, so we add 1.
            link.nb_messages = int(li.cssselect('dd.posts')[0].text.strip()) + 1
            yield link

class Post(object):
    def __init__(self, topic, id):
        self.id = int(id)
        self.topic = topic
        self.title = u''
        self.author = u''
        self.date = None
        self.content = u''
        self.signature = u''
        self.parent = 0

class TopicPage(PhpBBPage):
    def on_loaded(self):
        div = self.document.getroot().cssselect('div.pagination')[0]
        strongs = div.cssselect('strong')
        self.cur_page = int(strongs[0].text.strip())
        self.tot_pages = int(strongs[1].text.strip())

        v = urlsplit(self.url)
        args = parse_qs(v.query)
        self.topic_id = int(args['t'][0])

        self.forum_title = u''
        nav = self.parser.select(self.document.getroot(), 'li.icon-home')
        if len(nav) > 0:
            text = nav[0].findall('a')[-1].text.strip()
            if len(text) >= 20:
                text = text[:20] + u'…'
            self.forum_title = '[%s] ' % text

    def next_page_url(self):
        return self.document.getroot().cssselect('a.right-box')[0].attrib['href']

    def prev_page_url(self):
        return self.document.getroot().cssselect('a.left-box')[0].attrib['href']

    def iter_posts(self):
        for div in self.parser.select(self.document.getroot(), 'div.post'):
            yield self._get_post(div)

    def riter_posts(self):
        for div in reversed(self.parser.select(self.document.getroot(), 'div.post')):
            yield self._get_post(div)

    def get_post(self, id):
        parent = 0
        for div in self.parser.select(self.document.getroot(), 'div.post'):
            if div.attrib['id'] == 'p%d' % id:
                post = self._get_post(div)
                post.parent = parent
                return post
            else:
                parent = int(div.attrib['id'][1:])

    def _get_post(self, div):
        body = div.cssselect('div.postbody')[0]
        profile = div.cssselect('dl.postprofile')[0]

        id = div.attrib['id'][1:]
        post = Post(self.topic_id, id)

        title_tags = body.cssselect('h3 a')
        if len(title_tags) == 0:
            title_tags = self.document.getroot().cssselect('h2 a')
        if len(title_tags) == 0:
            title = u''
            self.logger.warning('Unable to parse title')
        else:
            title = title_tags[0].text.strip()

        post.title = self.forum_title + title
        for a in profile.cssselect('dt a'):
            if a.text:
                post.author = a.text.strip()

        p_tags = body.cssselect('p.author')
        if len(p_tags) == 0:
            p_tags = body.find('p')
        if len(p_tags) == 0:
            post.date = None
            self.logger.warning('Unable to parse datetime')
        else:
            p = p_tags[0]
            text = p.find('strong') and p.find('strong').tail
            if not text:
                text = p.text[4:]

            text = text.strip(u'» \n\r')
            try:
                post.date = parse_date(text)
            except ValueError:
                self.logger.warning(u'Unable to parse datetime "%s"' % text)

        post.content = self.parser.tostring(body.cssselect('div.content')[0])

        signature = body.cssselect('div.signature')
        if len(signature) > 0:
            post.signature = self.parser.tostring(signature[0])
        return post

    def get_last_post_id(self):
        id = 0
        for div in self.parser.select(self.document.getroot(), 'div.post'):
            id = int(div.attrib['id'][1:])
        return id

