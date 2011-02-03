# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


# python2.5 compatibility
from __future__ import with_statement

from weboob.capabilities.messages import ICapMessages, Message, Thread
from weboob.tools.backend import BaseBackend

from .browser import Newspaper20minutesBrowser


__all__ = ['Newspaper20minutesBackend']


class Newspaper20minutesBackend(BaseBackend, ICapMessages):
    NAME = 'minutes20'
    MAINTAINER = 'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = u'20minutes French news  website'
    #CONFIG = ValuesDict(Value('login',      label='Account ID'),
    #                    Value('password',   label='Password', masked=True))
    BROWSER = Newspaper20minutesBrowser

    def get_thread(self, id):
        if isinstance(id, Thread):
            thread = id
            id = thread.id
        else:
            thread = None

        with self.browser:
            content = self.browser.get_content(id)

        if not thread:
            thread = Thread(id)

        flags = Message.IS_HTML
        if not thread.id in self.storage.get('seen', default={}):
            flags |= Message.IS_UNREAD


        thread.title = content.title
        if not thread.date:
            thread.date = content.date

        #thread.root = Message(thread=thread, id=0, title=content.title, sender=content.author, receivers=None, date=thread.date, parent=None, content=content.body, signature=None, children = [], flags=flags)

        thread.root = Message(thread=thread, id=0, title=content.title, sender=content.author, receivers=None, date=thread.date, parent=None, content=content.body)
        return thread

    def set_message_read(self, message):
        raise NotImplementedError()
