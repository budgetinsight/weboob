# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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

from weboob.browser import AbstractBrowser


__all__ = ['CenetBrowser']


class CenetBrowser(AbstractBrowser):
    PARENT = 'caissedepargne'
    PARENT_ATTR = 'package.cenet.browser.CenetBrowser'
    BASEURL = 'https://www.espaceclient.credit-cooperatif.coop/'

    def __init__(self, nuser, *args, **kwargs):
        kwargs['domain'] = 'www.credit-cooperatif.coop'
        super(CenetBrowser, self).__init__(nuser, *args, **kwargs)
