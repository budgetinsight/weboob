# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Vincent Paredes
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from requests.exceptions import ConnectTimeout

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, ActionNeeded, BrowserPasswordExpired
from .pages import LoginPage, BillsPage
from .pages.login import ManageCGI, HomePage, PasswordPage
from .pages.bills import (
    SubscriptionsPage, SubscriptionsApiPage, BillsApiProPage, BillsApiParPage,
    ContractsPage,
)
from .pages.profile import ProfilePage
from weboob.browser.exceptions import ClientError, ServerError
from weboob.tools.compat import basestring
from weboob.tools.decorators import retry


__all__ = ['OrangeBillBrowser']


class OrangeBillBrowser(LoginBrowser):
    BASEURL = 'https://espaceclientv3.orange.fr'

    home_page = URL(r'https://businesslounge.orange.fr/$', HomePage)
    loginpage = URL(
        r'https://login.orange.fr/\?service=sosh&return_url=https://www.sosh.fr/',
        r'https://login.orange.fr/front/login',
        LoginPage,
    )
    password_page = URL(r'https://login.orange.fr/front/password', PasswordPage)

    contracts = URL(r'https://espaceclientpro.orange.fr/api/contracts\?page=1&nbcontractsbypage=15', ContractsPage)

    subscriptions = URL(r'https://espaceclientv3.orange.fr/js/necfe.php\?zonetype=bandeau&idPage=gt-home-page', SubscriptionsPage)
    subscriptions_api = URL(r'https://sso-f.orange.fr/omoi_erb/portfoliomanager/v2.0/contractSelector/users/current', SubscriptionsApiPage)

    manage_cgi = URL(r'https://eui.orange.fr/manage_eui/bin/manage.cgi', ManageCGI)

    # is billspage deprecated ?
    billspage = URL(
        r'https://m.espaceclientv3.orange.fr/\?page=factures-archives',
        r'https://.*.espaceclientv3.orange.fr/\?page=factures-archives',
        r'https://espaceclientv3.orange.fr/\?page=factures-archives',
        r'https://espaceclientv3.orange.fr/\?page=facture-telecharger',
        r'https://espaceclientv3.orange.fr/maf.php',
        r'https://espaceclientv3.orange.fr/\?idContrat=(?P<subid>.*)&page=factures-historique',
        r'https://espaceclientv3.orange.fr/\?page=factures-historique&idContrat=(?P<subid>.*)',
        BillsPage,
    )

    bills_api_pro = URL(
        r'https://espaceclientpro.orange.fr/api/contract/(?P<subid>\d+)/bills\?count=(?P<count>)',
        BillsApiProPage,
    )

    bills_api_par = URL(r'https://sso-f.orange.fr/omoi_erb/facture/v2.0/billsAndPaymentInfos/users/current/contracts/(?P<subid>\d+)', BillsApiParPage)
    doc_api_par = URL(r'https://sso-f.orange.fr/omoi_erb/facture/v1.0/pdf')

    doc_api_pro = URL('https://espaceclientpro.orange.fr/api/contract/(?P<subid>\d+)/bill/(?P<dir>.*)/(?P<fact_type>.*)/\?(?P<billparams>)')
    profile = URL('/\?page=profil-infosPerso', ProfilePage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        try:
            self.loginpage.stay_or_go().login(self.username, self.password)
        except ClientError as error:
            if error.response.status_code == 401:
                raise BrowserIncorrectPassword()
            if error.response.status_code == 403:
                # occur when user try several times with a bad password, orange block his account for a short time
                raise BrowserIncorrectPassword(error.response.json())
            raise

        if self.password_page.is_here():
            error_message = self.page.get_change_password_message()
            if error_message:
                raise BrowserPasswordExpired(error_message)

    def get_nb_remaining_free_sms(self):
        raise NotImplementedError()

    def post_message(self, message, sender):
        raise NotImplementedError()

    def _iter_subscriptions_by_type(self, name, _type):
        self.location('https://espaceclientv3.orange.fr/?page=gt-home-page&%s' % _type)
        self.subscriptions.go()
        for sub in self.page.iter_subscription():
            sub.subscriber = name
            yield sub

    @retry(BrowserUnavailable, tries=2, delay=10)
    @need_login
    def get_subscription_list(self):
        try:
            self.profile.go()

            assert self.profile.is_here() or self.manage_cgi.is_here()

            # we land on manage_cgi page when there is cgu to validate
            if self.manage_cgi.is_here():
                # but they are not in this page, we have to go to home_page to get message
                self.home_page.go()
                msg = self.page.get_error_message()
                assert "Nos Conditions Générales d'Utilisation ont évolué" in msg, msg
                raise ActionNeeded(msg)
            else:
                profile = self.page.get_profile()
        except ConnectTimeout:
            # sometimes server just doesn't answer
            raise BrowserUnavailable()

        # this only works when there are pro subs.
        nb_sub = 0
        try:
            for sub in self.contracts.go().iter_subscriptions():
                sub.subscriber = profile.name
                yield sub
            nb_sub = self.page.doc['totalContracts']
            # assert pagination is not needed
            assert nb_sub < 15
        except ServerError:
            pass

        if nb_sub > 0:
            return
        # if nb_sub is 0, we continue, because we can get them in next url

        for sub in self._iter_subscriptions_by_type(profile.name, 'sosh'):
            nb_sub += 1
            yield sub
        for sub in self._iter_subscriptions_by_type(profile.name, 'orange'):
            nb_sub += 1
            yield sub

        if nb_sub == 0:
            # No subscriptions found, trying with the API.
            headers = {
                'X-Orange-Caller-Id': 'ECQ',
            }
            self.subscriptions_api.go(headers=headers)
            for sub in self.page.iter_subscription():
                sub.subscriber = profile.name
                yield sub

    @need_login
    def iter_documents(self, subscription):
        documents = []
        if subscription._is_pro:
            for d in self.bills_api_pro.go(subid=subscription.id, count=72).get_bills(subid=subscription.id):
                documents.append(d)
            # check pagination for this subscription
            assert len(documents) != 72
        else:
            headers = {'x-orange-caller-id': 'ECQ'}
            self.bills_api_par.go(subid=subscription.id, headers=headers)
            for b in self.page.get_bills(subid=subscription.id):
                documents.append(b)
        return iter(documents)

    @need_login
    def get_profile(self):
        return self.profile.go().get_profile()
