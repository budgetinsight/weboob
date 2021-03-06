# -*- coding: utf-8 -*-

# Copyright(C) 2015 Matthieu Weber
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.capabilities.weather import CapWeather, CityNotFound
from weboob.tools.backend import Module
from weboob.capabilities.base import find_object
from .browser import IlmatieteenlaitosBrowser


__all__ = ['IlmatieteenlaitosModule']


class IlmatieteenlaitosModule(Module, CapWeather):
    NAME = 'ilmatieteenlaitos'
    MAINTAINER = u'Matthieu Weber'
    EMAIL = 'mweber+weboob@free.fr'
    VERSION = '1.6'
    DESCRIPTION = 'Get forecasts from the Ilmatieteenlaitos.fi website'
    LICENSE = 'AGPLv3+'
    BROWSER = IlmatieteenlaitosBrowser

    def get_current(self, city_id):
        return self.browser.get_current(self.get_city(city_id))

    def iter_forecast(self, city_id):
        return self.browser.iter_forecast(self.get_city(city_id))

    def iter_city_search(self, pattern):
        return self.browser.iter_city_search(pattern)

    def get_city(self, _id):
        return find_object(self.iter_city_search(_id), id=_id, error=CityNotFound)
