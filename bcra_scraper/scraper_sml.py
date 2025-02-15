from csv import DictWriter
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import reduce
import logging

from bs4 import BeautifulSoup

import pandas as pd

from bcra_scraper.exceptions import InvalidConfigurationError
from bcra_scraper.scraper_base import BCRAScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BCRASMLScraper(BCRAScraper):

    """
    Clase que representa un Scraper para la tasa SML
    del BCRA (Banco Central de la República Argentina).


    Attributes
    ----------
    url : str
        Una cadena que representa una url válida, usada para obtener
        el contenido a ser scrapeado
    coins : Dict
        Diccionario que contiene las monedas que serán utilizadas

    Methods
    -------
    fetch_contents(coins)
        Obtiene los contenidos a ser parseados

    fetch_content(coins)
        Retorna el contenido de la moneda

    parse_contents(contents, start_date, end_date)
        Recibe un iterable de contenidos y devuelve un iterable con la
        información scrapeada

    parse_content(content, coin, start_date, end_date)
        Regresa un iterable con el contenido parseado

    run(start_date, end_date)
        Llama a los métodos que obtienen y scrapean los contenidos
        y los devuelve en un iterable
    """

    def __init__(self, url, coins, intermediate_panel_path, *args, **kwargs):
        """
        Parameters
        ----------
        url : str
            Una cadena que representa una url válida, usada para obtener
            el contenido a ser scrapeado. Una URL se considera válida cuando su
            contenido no está vacio.
        coins : Dict
            Diccionario que contiene los nombres de las monedas
        """

        self.coins = coins
        self.intermediate_panel_path = intermediate_panel_path
        super(BCRASMLScraper, self)\
            .__init__(url, *args, **kwargs)

    def fetch_contents(self, start_date, end_date):
        """
        Función que a traves de un loop llama a un método
        y regresa un diccionario con el html de cada moneda.

        Parameters
        ----------
        coins : Dict
            Diccionario que contiene las monedas
        """

        contents = {}
        for k, v in self.coins.items():

            fetched = self.fetch_content(v)
            if fetched:
                contents[k] = fetched
        return contents

    def validate_coin_in_configuration_file(self, coin, options):
        """
        Valida que el valor de la moneda en el archivo de configuración
        se corresponda con los valores de las opciones del select en la página
        """
        select_options = [select_option.text for select_option in options]
        if coin in select_options:
            return True
        else:
            return False

    def fetch_content(self, coin):
        """
        Ingresa al navegador y utiliza la moneda
        regresando el contenido que pertenece a la misma.

        Parameters
        ----------
        coins : String
            String que contiene el nombre de la moneda
        """
        content = ''
        counter = 1
        tries = self.tries

        while counter <= tries:
            try:
                browser_driver = self.get_browser_driver()
                browser_driver.get(self.url)
                element_present = EC.presence_of_element_located(
                    (By.NAME, 'moneda')
                )
                element = WebDriverWait(browser_driver, 0).until(element_present)

                options = element.find_elements_by_tag_name('option')
                valid = self.validate_coin_in_configuration_file(coin, options)
                if valid:
                    element.send_keys(coin)
                    content = browser_driver.page_source
            except TimeoutException:
                if counter < tries:
                    logging.warning(
                        f'La conexion de internet ha fallado para la moneda {coin}. Reintentando...'
                    )
                    counter = counter + 1
                else:
                    logging.warning(
                        f'La conexion de internet ha fallado para la moneda {coin}'
                    )
                    raise InvalidConfigurationError(
                        f'La conexion de internet ha fallado para la moneda {coin}'
                    )
            except NoSuchElementException:
                raise InvalidConfigurationError(
                    f'La conexion de internet ha fallado para la moneda {coin}'
                )

            break

        return content

    def parse_contents(self, contents, start_date, end_date):
        """
        Recorre un iterable que posee los html y llama a un método.
        Retorna un diccionario con las monedas como clave y como valor
        una lista con un diccionario.

        Parameters
        ----------
        contents : Dict
            String con nombre de cada moneda como clave, string con cada html
            como valor
        start_date : date
            fecha de inicio que va a tomar como referencia el scraper
        end_date : date
            fecha de fin que va a tomar como referencia el scraper
        """

        parsed_contents = []
        parsed_peso_uruguayo, parsed_real = {}, {}
        parsed_contents = {'peso_uruguayo': [], 'real': []}

        for k, v in contents.items():

            parsed = self.parse_content(v, k, start_date, end_date)

            if parsed:
                for p in parsed:
                    if p['coin'] == 'peso_uruguayo':
                        if p['indice_tiempo'] not in(
                            parsed_peso_uruguayo.keys()
                        ):
                            parsed_peso_uruguayo[p['indice_tiempo']] = {}
                        parsed_peso_uruguayo[p['indice_tiempo']][
                            'Tipo de cambio de Referencia'
                            ] = p['Tipo de cambio de Referencia']
                        parsed_peso_uruguayo[p['indice_tiempo']][
                            'Tipo de cambio URINUSCA'
                            ] = p['Tipo de cambio URINUSCA']
                        parsed_peso_uruguayo[p['indice_tiempo']][
                            'Tipo de cambio SML Peso Uruguayo'
                            ] = p['Tipo de cambio SML Peso Uruguayo']
                        parsed_peso_uruguayo[p['indice_tiempo']][
                            'Tipo de cambio SML Uruguayo Peso'
                            ] = p['Tipo de cambio SML Uruguayo Peso']

                    else:
                        if p['indice_tiempo'] not in parsed_real.keys():
                            parsed_real[p['indice_tiempo']] = {}
                        parsed_real[p['indice_tiempo']][
                            'Tipo de cambio de Referencia'
                            ] = p['Tipo de cambio de Referencia']
                        parsed_real[p['indice_tiempo']][
                            'Tipo de cambio PTAX'
                            ] = p['Tipo de cambio PTAX']
                        parsed_real[p['indice_tiempo']][
                            'Tipo de cambio SML Peso Real'
                            ] = p['Tipo de cambio SML Peso Real']
                        parsed_real[p['indice_tiempo']][
                            'Tipo de cambio SML Real Peso'
                            ] = p['Tipo de cambio SML Real Peso']

        for k, v in parsed_peso_uruguayo.items():

            v['indice_tiempo'] = k
            parsed_contents['peso_uruguayo'].append(v)

        for k, v in parsed_real.items():
            v['indice_tiempo'] = k
            parsed_contents['real'].append(v)

        return parsed_contents

    def parse_content(self, content, coin, start_date, end_date):
        """
        Retorna un iterable con el contenido scrapeado cuyo formato
        posee la moneda, el indice de tiempo, y los tipo de cambio
        correspondientes a la moneda.

        Parameters
        ----------
        content: str
            Html de la moneda
        coin : str
            Nombre de la moneda
        start_date : date
            fecha de inicio que va a tomar como referencia el scraper
        end_date : date
            fecha de fin que va a tomar como referencia el scraper
        """

        soup = BeautifulSoup(content, "html.parser")
        try:
            table = soup.find('table')

            if not table:
                return []

            head = table.find('thead')

            if not head:
                return []

            body = table.find('tbody')

            if not body:
                return []

            head_rows = head.find_all('tr')
            parsed_content = []
            day_count = (end_date - start_date).days + 1

            for single_date in (start_date + timedelta(n)
                            for n in range(day_count)):
                day = single_date.strftime("%d/%m/%Y")
                for header in head_rows:
                    headers = header.find_all('th')
                    parsed = {}
                    parsed['coin'] = coin
                    parsed['indice_tiempo'] = day
                    parsed[headers[1].text] = ''
                    parsed[headers[2].text] = ''
                    parsed[headers[3].text] = ''
                    parsed[headers[4].text] = ''

                    if body.find('td', text=day):
                        row = body.find('td', text=day).parent
                        cols = row.find_all('td')
                        parsed['coin'] = coin
                        parsed['indice_tiempo'] = cols[0].text
                        parsed[headers[1].text] = cols[1].text.strip()
                        parsed[headers[2].text] = cols[2].text.strip()
                        parsed[headers[3].text] = cols[3].text.strip()
                        parsed[headers[4].text] = cols[4].text.strip()
                    parsed_content.append(parsed)

            return parsed_content
        except:
            return []

    def _preprocess_rows(self, parsed):

        parsed['peso_uruguayo'] = self.preprocess_rows(
            parsed['peso_uruguayo']
            )
        parsed['real'] = self.preprocess_rows(parsed['real'])

        return parsed

    def preprocess_rows(self, rows):
        """
        Regresa un iterable donde la fecha y los valores son parseados.

        Parameters
        ----------
        rows : list
        """
        preprocessed_rows = []

        for row in rows:
            preprocessed_row = {}

            for k in row.keys():
                if k == 'indice_tiempo':
                    if '/' in row[k]:
                        _ = row[k].split('/')
                        preprocessed_date = date.fromisoformat(
                            '-'.join([_[2], _[1], _[0]])
                        )
                    else:
                        preprocessed_date = date.fromisoformat(row[k])
                    preprocessed_row['indice_tiempo'] = preprocessed_date
                else:
                    if row[k]:
                        preprocessed_row[k] = (
                            Decimal((row[k]).replace(',', '.'))
                            if isinstance(row[k], str)
                            else row[k]
                        )
                    else:
                        preprocessed_row[k] = row[k]

            preprocessed_rows.append(preprocessed_row)

        return preprocessed_rows

    def get_intermediate_panel_data_from_parsed(self, parsed):
        """
        Recorre parsed y por cada tipo de cambio genera un diccionario
        obteniendo por separado las claves que se utilizaran como headers,
        y sus valores.

        Parameters
        ----------
        parsed : lista de diccionarios por moneda
        """
        intermediate_panel_data = []

        if parsed:
            for c in self.coins.keys():
                if c == 'peso_uruguayo':
                    types = [
                        'Tipo de cambio de Referencia',
                        'Tipo de cambio URINUSCA',
                        'Tipo de cambio SML Peso Uruguayo',
                        'Tipo de cambio SML Uruguayo Peso',
                    ]
                else:
                    types = [
                        'Tipo de cambio de Referencia',
                        'Tipo de cambio PTAX',
                        'Tipo de cambio SML Peso Real',
                        'Tipo de cambio SML Real Peso',
                    ]

                for r in parsed[c]:
                    for type in types:
                        if type in r.keys():
                            panel_row = {
                                'indice_tiempo': r['indice_tiempo'],
                                'coin': c,
                                'type': type,
                                'value': r[type],
                            }
                            intermediate_panel_data.append(panel_row)
        else:
            return []
        intermediate_panel_data.reverse()
        return intermediate_panel_data

    def parse_from_intermediate_panel(self, start_date, end_date):
        """
        Lee el dataframe del panel intermedio.
        Retorna un diccionario con las monedas como clave y como valor
        una lista con un diccionario.
        Parameters
        ----------
        start_date : date
            Fecha de inicio que toma como referencia el scraper
        end_date : date
            fecha de fin que va a tomar como referencia el scraper
        """
        parsed = {'peso_uruguayo': [], 'real': []}
        coin_dfs = {}
        intermediate_panel_df = self.read_intermediate_panel_dataframe()
        intermediate_panel_df.set_index(['indice_tiempo'], inplace=True)

        if not intermediate_panel_df.empty:
            coin_dfs = {'peso_uruguayo': {}, 'real': {}}
            for k in self.coins.keys():
                if k == 'peso_uruguayo':
                    for type in [
                        'Tipo de cambio de Referencia',
                        'Tipo de cambio URINUSCA',
                        'Tipo de cambio SML Peso Uruguayo',
                        'Tipo de cambio SML Uruguayo Peso'
                    ]:
                        coin_dfs[k][type] = intermediate_panel_df.loc[
                            (intermediate_panel_df['type'] == type) &
                            (intermediate_panel_df['coin'] == k)
                        ][['value']]
                        coin_dfs[k][type].rename(
                            columns={'value': f'{k}_{type}'}, inplace=True
                        )
                        if coin_dfs[k][type].empty:
                            (coin_dfs[k][type] == '0.0')
                else:
                    for type in [
                        'Tipo de cambio de Referencia',
                        'Tipo de cambio PTAX',
                        'Tipo de cambio SML Peso Real',
                        'Tipo de cambio SML Real Peso'
                    ]:
                        coin_dfs[k][type] = intermediate_panel_df.loc[
                            (intermediate_panel_df['type'] == type) &
                            (intermediate_panel_df['coin'] == k)
                        ][['value']]
                        coin_dfs[k][type].rename(
                            columns={'value': f'{k}_{type}'}, inplace=True
                        )
                        if coin_dfs[k][type].empty:
                            (coin_dfs[k][type] == '0.0')

            coins_df = {}
            for type in ['peso_uruguayo', 'real']:
                coins_df[type] = reduce(
                    lambda df1, df2: df1.merge(
                        df2, left_on='indice_tiempo', right_on='indice_tiempo'
                    ),
                    coin_dfs[type].values(),
                )

            for type in ['peso_uruguayo', 'real']:
                for r in coins_df[type].to_records():
                    if (start_date <= r[0] and
                       r[0] <= end_date):
                        parsed_row = {}

                        columns = ['indice_tiempo']
                        columns.extend([v for v in coin_dfs[type].keys()])

                        for index, column in enumerate(columns):
                            parsed_row[column] = r[index]

                        if parsed_row:
                            parsed[type].append(parsed_row)
        parsed['peso_uruguayo'].reverse()
        parsed['real'].reverse()
        return parsed

    def write_intermediate_panel(self, rows, intermediate_panel_path):
        """
        Escribe el panel intermedio.

        Parameters
        ----------
        rows: Iterable
        """
        header = ['indice_tiempo', 'coin', 'type', 'value']

        with open(intermediate_panel_path, 'w') as intermediate_panel:
            writer = DictWriter(intermediate_panel, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

    def read_intermediate_panel_dataframe(self):
        """
        Lee el dataframe
        """
        intermediate_panel_dataframe = None

        try:
            intermediate_panel_dataframe = pd.read_csv(
                'sml-intermediate-panel.csv',
                converters={
                    'serie_tiempo': lambda _: _,
                    'coin': lambda _: str(_),
                    'type': lambda _: str(_),
                    'value': lambda _: str(_)
                }
            )

        except FileNotFoundError:
            raise InvalidConfigurationError(
                "El archivo panel no existe"
            )
        return intermediate_panel_dataframe

    def save_intermediate_panel(self, parsed):
        """
        Llama a un método para obtener la data del panel intermedio
        y a otro método pasandole esa data para que la escriba.

        Parameters
        ----------
        parsed: Iterable
        """
        intermediate_panel_data = self.get_intermediate_panel_data_from_parsed(
            parsed
        )
        self.write_intermediate_panel(intermediate_panel_data, self.intermediate_panel_path)
