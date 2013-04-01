# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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


import urllib
from urlparse import urlparse, parse_qs
from decimal import Decimal
import re

from weboob.tools.browser import BasePage, BrowserIncorrectPassword
from weboob.tools.ordereddict import OrderedDict
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(BasePage):
    def login(self, login, passwd):
        self.browser.select_form(name='ident')
        self.browser['_cm_user'] = login
        self.browser['_cm_pwd'] = passwd
        self.browser.submit(nologin=True)


class LoginErrorPage(BasePage):
    pass


class ChangePasswordPage(BasePage):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Please change your password')

class VerifCodePage(BasePage):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Unable to login: website asks a code from a card')

class InfoPage(BasePage):
    pass


class EmptyPage(BasePage):
    pass


class TransfertPage(BasePage):
    pass


class UserSpacePage(BasePage):
    pass


class AccountsPage(BasePage):
    def get_list(self):
        accounts = OrderedDict()

        for tr in self.document.getiterator('tr'):
            first_td = tr.getchildren()[0]
            if (first_td.attrib.get('class', '') == 'i g' or first_td.attrib.get('class', '') == 'p g') \
               and first_td.find('a') is not None:

                a = first_td.find('a')
                link = a.get('href', '')
                if link.startswith('POR_SyntheseLst'):
                    continue

                url = urlparse(link)
                p = parse_qs(url.query)
                if not 'rib' in p:
                    continue

                for i in (2,1):
                    balance = FrenchTransaction.clean_amount(tr.getchildren()[i].text)
                    currency = Account.get_currency(tr.getchildren()[i].text)
                    if len(balance) > 0:
                        break
                balance = Decimal(balance)

                id = p['rib'][0]
                if id in accounts:
                    account = accounts[id]
                    if not account.coming:
                        account.coming = Decimal('0.0')
                    account.coming += balance
                    account._card_links.append(link)
                    continue

                account = Account()
                account.id = id
                account.label = unicode(a.text).strip().lstrip(' 0123456789').title()
                account._link_id = link
                account._card_links = []

                account.balance = balance
                account.currency = currency

                accounts[account.id] = account

        return accounts.itervalues()


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) CARTE \d+ PAIEMENT CB\s+(?P<dd>\d{2})(?P<mm>\d{2}) ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE \d+'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE$'),                  FrenchTransaction.TYPE_CHECK),
                (re.compile('^COTIS\.? (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),      FrenchTransaction.TYPE_DEPOSIT),
               ]

    _is_coming = False


class OperationsPage(BasePage):
    def get_history(self):
        index = 0
        for tr in self.document.getiterator('tr'):
            # columns can be:
            # - date | value | operation | debit | credit | contre-valeur
            # - date | value | operation | debit | credit
            # - date | operation | debit | credit
            # That's why we skip any extra columns, and take operation, debit
            # and credit from last instead of first indexes.
            tds = tr.getchildren()[:5]
            if len(tds) < 4:
                continue

            if tds[0].attrib.get('class', '') == 'i g' or \
               tds[0].attrib.get('class', '') == 'p g' or \
               tds[0].attrib.get('class', '').endswith('_c1 c _c1'):
                operation = Transaction(index)
                index += 1

                parts = [txt.strip() for txt in tds[-3].itertext() if len(txt.strip()) > 0]

                # To simplify categorization of CB, reverse order of parts to separate
                # location and institution.
                if parts[0].startswith('PAIEMENT CB'):
                    parts.reverse()

                operation.parse(date=tds[0].text,
                                raw=u' '.join(parts))

                credit = u''.join([txt.strip() for txt in tds[-1].itertext()])
                debit = u''.join([txt.strip() for txt in tds[-2].itertext()])
                operation.set_amount(credit, debit)
                yield operation

    def go_next(self):
        form = self.document.xpath('//form[@id="paginationForm"]')
        if len(form) == 0:
            return False

        form = form[0]

        text = self.parser.tocleanstring(form)
        m = re.search(u'(\d+) / (\d+)', text or '', flags=re.MULTILINE)
        if not m:
            return False

        cur = int(m.group(1))
        last = int(m.group(2))

        if cur == last:
            return False

        inputs = {}
        for elm in form.xpath('.//input[@type="input"]'):
            key = elm.attrib['name']
            value = elm.attrib['value']
            inputs[key] = value

        inputs['page'] = str(cur + 1)

        self.browser.location(form.attrib['action'], urllib.urlencode(inputs))

        return True


class CardPage(OperationsPage):
    def get_history(self):
        index = 0
        for tr in self.document.xpath('//table[@class="liste"]/tbody/tr'):
            tds = tr.findall('td')[:4]
            if len(tds) < 4:
                continue

            tr = Transaction(index)

            parts = [txt.strip() for txt in list(tds[-3].itertext()) + list(tds[-2].itertext()) if len(txt.strip()) > 0]

            tr.parse(date=tds[0].text.strip(' \xa0'),
                     raw=u' '.join(parts))
            tr.type = tr.TYPE_CARD

            tr.set_amount(tds[-1].text)
            yield tr


class NoOperationsPage(OperationsPage):
    def get_history(self):
        return iter([])
