#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests del modulo bcrascraper."""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import with_statement

from datetime import date, timedelta
import unittest
from unittest import mock

from bs4 import BeautifulSoup

from bcra_scraper.scraper import Libor_scraper
from bcra_scraper.utils import get_most_recent_previous_business_day
from bcra_scraper.bcra_scraper import write_tasas_libor


class BcraLiborScraperTestCase(unittest.TestCase):

    def test_get_last_business_day(self):
        assert date(2019, 3, 15) == get_most_recent_previous_business_day(date(2019, 3, 18))
        assert date(2019, 3, 18) == get_most_recent_previous_business_day(date(2019, 3, 19))
        assert date(2019, 3, 22) == get_most_recent_previous_business_day(date(2019, 3, 24))

    def test_fetch_content_with_valid_dates(self):
        scraper = Libor_scraper()
        start_day = date(2019, 3, 4)
        end_day = date(2019, 3, 10)

        contents = scraper.fetch_content(start_day, end_day)

        assert len(contents) == 7

    def test_fetch_content_with_invalid_dates(self):
        scraper = Libor_scraper()
        start_day = date(2019, 3, 10)
        end_day = date(2019, 3, 4)

        contents = scraper.fetch_content(start_day, end_day)

        assert contents == []

    # TODO: rename test name
    def test_get_content_for_a_non_business_day(self):
        scraper = Libor_scraper()
        content_date = date.today()
        content = scraper.fetch_day_content(content_date)

        soup = BeautifulSoup(content, "html.parser")

        table = soup.find('table')
        head = table.find('thead') if table else None
        body = table.find('tbody') if table else None

        assert table is not None
        assert head is not None
        assert body is None

    # TODO: rename test name
    def test_get_content_for_a_business_day(self):
        scraper = Libor_scraper()
        content_date = get_most_recent_previous_business_day(
            date.today() - timedelta(days=1)
            )
        content = scraper.fetch_day_content(content_date)

        soup = BeautifulSoup(content, "html.parser")

        table = soup.find('table')
        head = table.find('thead') if table else None
        body = table.find('tbody') if table else None

        assert table is not None
        assert head is not None
        assert body is not None

    def test_parse_for_empty_contents(self):
        scraper = Libor_scraper()
        contents = []
        parsed = scraper.parse(contents)

        assert parsed == []

    def test_parse_for_non_empty_contents(self):
        scraper = Libor_scraper()
        
        empty_table_content = '''
        <table class="table table-BCRA table-bordered table-hover table-responsive">
            <thead>
                <tr><th>No existen registros</th></tr>
            </thead>
        </table>
        '''

        contents = [empty_table_content]

        parsed = scraper.parse(contents)

        assert parsed == []

    def test_scraper_with_empty_table(self):
        content = '''
        <table class="table table-BCRA table-bordered table-hover table-responsive">
            <thead>
                <tr><th>No existen registros</th></tr>
            </thead>
        </table>
        '''
        scraper = Libor_scraper()

        result = scraper.parse_day_content(content)

        assert result == {}

    def test_scraper_with_valid_table(self):
        content = '''
        	<table class="table table-BCRA table-bordered table-hover table-responsive">
        <thead>
            <tr>
                <th colspan="2" align="left">Tasa LIBOR al:  15/03/2019</th>
            </tr>
            <tr>
                <th>Plazo en días</th>
                <th>Tasa (T.N.A. %)</th>
            </tr>
        </thead>
        <tbody>
			<tr>
				<td>30</td>
				<td>2,481750</td>
			</tr>
			<tr>
				<td>60</td>
				<td>2,558380</td>
			</tr>
			<tr>
				<td>90</td>
				<td>2,625250</td>
			</tr>
			<tr>
				<td>180</td>
				<td>2,671750</td>
			</tr>
			<tr>
				<td>360</td>
				<td>2,840500</td>
			</tr>
		</tbody>
	</table>
        '''
        scraper = Libor_scraper()

        result = scraper.parse_day_content(content)

        assert result.get('indice_tiempo') == '15/03/2019'
        assert result.get('30') == '2,481750'
        assert result.get('60') == '2,558380'
        assert result.get('90') == '2,625250'
        assert result.get('180') == '2,671750'
        assert result.get('360') == '2,840500'

    def test_run_with_valid_dates(self):
        scraper = Libor_scraper()
        
        start_date = date(2019, 3, 4)

        end_date = date(2019, 3, 6)

        parsed = scraper.run(start_date, end_date)

        assert len(parsed) == 3

    def test_run_with_non_valid_dates(self):
        scraper = Libor_scraper()
        
        start_date = date(2019, 3, 10)

        end_date = date(2019, 3, 9)

        parsed = scraper.run(start_date, end_date)

        assert parsed == []
