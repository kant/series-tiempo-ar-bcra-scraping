from csv import DictWriter
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import reduce
import logging
import re

from bs4 import BeautifulSoup
from pandas import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from bcra_scraper.exceptions import InvalidConfigurationError
from bcra_scraper.scraper_base import BCRAScraper


class BCRATCEScraper(BCRAScraper):

    """
    Clase que representa un Scraper para el tipo de cambio de entidades
    bancarias del BCRA (Banco Central de la República Argentina).

    Attributes
    ----------
    url : str
        Una cadena que representa una url válida, usada para obtener
        el contenido a ser scrapeado
    coins : Dict
        Diccionario que contiene las monedas que serán utilizadas
    entities : Dict
        Diccionario que contiene el nombre de los bancos

    Methods
    -------
    fetch_contents(start_date, end_date, coins)
        Devuelve una lista de diccionarios para cada moneda
        en cada fecha con el html correspondiente.

    fetch_content(single_date, coin)
        Regresa un string  con el contenido que pertenece a la moneda.

    parse_contents(contents, start_date, end_date)
        Retorna un diccionario que tiene como clave cada moneda
        y como valor una lista con un diccionario que tiene los
        contenidos parseados.

    parse_content(content, start_date, end_date, coin)
        Retorna un iterable con un diccionario.

    run(start_date, end_date)
        Llama a los métodos que obtienen y scrapean los contenidos
        y los devuelve en un iterable
    """

    def __init__(self, url, coins, entities, intermediate_panel_path, *args, **kwargs):
        """
        Parameters
        ----------
        url : str
            Una cadena que representa una url válida, usada para obtener
            el contenido a ser scrapeado. Una URL se considera válida cuando su
            contenido no está vacio.
        coins : Dict
            Diccionario que contiene los nombres de las monedas
        entities : Dict
            Diccionario que contiene el nombre de los bancos
        """
        self.coins = coins
        self.entities = entities
        self.intermediate_panel_path = intermediate_panel_path
        super(BCRATCEScraper, self)\
            .__init__(url, *args, **kwargs)

    def fetch_contents(self, start_date, end_date):
        """
        Recorre rango de fechas y verifica que la fecha corresponda
        a un día habil. Devuelve una lista de diccionarios para cada moneda
        en cada fecha con el html correspondiente.

        Parameters
        ----------
        start_date : date
            fecha de inicio que va a tomar como referencia el scraper
        end_date: date
            fecha de fin que va a tomar como referencia el scraper
        coins : Dict
            Diccionario que contiene los nombres de las monedas
        """
        contents = []

        day_count = (end_date - start_date).days + 1

        for single_date in (start_date + timedelta(n)
                            for n in range(day_count)):
            for k, v in self.coins.items():
                content = {}
                fetched = self.fetch_content(single_date, v)
                if fetched:
                    content[k] = fetched
                contents.append(content)
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

    def fetch_content(self, single_date, coin):
        """
        Ingresa al navegador y utiliza la moneda
        regresando el contenido que pertenece a la misma.

        Parameters
        ----------
        single_date : date
            Fecha de inicio que toma como referencia el scraper
        coin : String
            String que contiene el nombre de la moneda
        """
        content_dict = {}
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
                    browser_driver.execute_script(
                        'document.getElementsByName("fecha")\
                        [0].removeAttribute("readonly")')
                    elem = browser_driver.find_element_by_name('fecha')
                    elem.send_keys(single_date.strftime("%d/%m/%Y"))
                    submit_button = browser_driver.find_element_by_class_name(
                        'btn-primary')
                    submit_button.click()
                    content = browser_driver.page_source
                    content_dict['indice_tiempo'] = f'{single_date.strftime("%Y-%m-%d")}'
                    content_dict['content'] = content

            except TimeoutException:
                if counter < tries:
                    logging.warning(
                        f'La conexion de internet ha fallado para la fecha {single_date}. Reintentando...'
                    )
                    counter = counter + 1
                else:
                    logging.warning(
                        f'La conexion de internet ha fallado para la fecha {single_date}'
                    )
                    raise InvalidConfigurationError(
                        f'La conexion de internet ha fallado para la fecha {single_date}'
                    )
            except NoSuchElementException:
                raise InvalidConfigurationError(
                    f'La conexion de internet ha fallado para la fecha {single_date}'
                )

            break

        return content_dict

    def get_intermediate_panel_data_from_parsed(self, parsed):
        """
        Recorre parsed y por cada registro genera un diccionario
        obteniendo por separado las claves que se utilizaran como headers,
        y sus valores.

        Parameters
        ----------
        parsed : lista de diccionarios por moneda
        """
        intermediate_panel_data = []

        parsed_contents = {'dolar': [], 'euro': []}

        for p in parsed:
            for k, v in p.items():
                if k == 'indice_tiempo':
                    time = p['indice_tiempo']
                else:
                    result = k.split("_")
                    if result[2] == 'dolar':
                        panel = {}
                        panel['indice_tiempo'] = time
                        panel['coin'] = result[2]
                        panel['entity'] = result[3]
                        panel['channel'] = result[4]
                        panel['flow'] = result[5]
                        panel['hour'] = result[6]
                        panel['value'] = v
                        parsed_contents['dolar'].append(panel)
                    elif result[2] == 'euro':
                        panel = {}
                        panel['indice_tiempo'] = time
                        panel['coin'] = result[2]
                        panel['entity'] = result[3]
                        panel['channel'] = result[4]
                        panel['flow'] = result[5]
                        panel['hour'] = result[6]
                        panel['value'] = v
                        parsed_contents['euro'].append(panel)
        intermediate_panel_data.extend(
            parsed_contents['dolar'] + parsed_contents['euro']
        )
        intermediate_panel_data.reverse()
        return intermediate_panel_data

    def parse_from_intermediate_panel(self, start_date, end_date):
        """
        Lee el dataframe del panel intermedio.
        Unifica los valores de coin, entity, channel, flow, hour,
        convirtiendolos en clave y como valor se asigna el dato
        de la clave value.
        Regresa un diccionario con las monedas como claves, y como valor
        una lista con un diccionario que contiene la fecha y los registros.

        Parameters
        ----------
        start_date : date
            Fecha de inicio que toma como referencia el scraper
        end_date : date
            fecha de fin que va a tomar como referencia el scraper
        """
        parsed = {'dolar': [], 'euro': []}
        coin_dfs = {}

        intermediate_panel_df = self.read_intermediate_panel_dataframe()
        intermediate_panel_df.set_index(['indice_tiempo'], inplace=True)

        if not intermediate_panel_df.empty:
            coin_dfs = {'dolar': {}, 'euro': {}}

            for coin in ['dolar', 'euro']:
                for entity in self.entities:
                    for channel in ['mostrador', 'electronico']:
                        for flow in ['compra', 'venta']:
                            for hour in [11, 13, 15]:
                                for k in self.coins.keys():
                                    type =\
                                        (
                                            f'tc_ars_{k}_{entity}_{channel}_'
                                            f'{flow}_{hour}hs'
                                        )
                                    coin_dfs[k][type] =\
                                        intermediate_panel_df.loc[
                                        (intermediate_panel_df[
                                            'coin'] == k) &
                                        (intermediate_panel_df[
                                            'entity'] == entity) &
                                        (intermediate_panel_df[
                                            'channel'] == channel) &
                                        (intermediate_panel_df[
                                            'flow'] == flow) &
                                        (intermediate_panel_df[
                                            'hour'] == f'{hour}hs')
                                    ][['value']]

                                    coin_dfs[k][type].rename(
                                        columns={'value': f'{type}'},
                                        inplace=True
                                    )
                                    if coin_dfs[k][type].empty:
                                        del(coin_dfs[k][type])

            coins_df = {}
            for coin in ['dolar', 'euro']:
                coins_df[coin] = reduce(
                    lambda df1, df2: df1.merge(
                        df2, left_on='indice_tiempo', right_on='indice_tiempo'
                    ),
                    coin_dfs[coin].values(),
                )

            for coin in ['dolar', 'euro']:
                for r in coins_df[coin].to_records():
                    if (start_date <= r[0] and
                       r[0] <= end_date):
                        parsed_row = {}

                        columns = ['indice_tiempo']
                        columns.extend([v for v in coin_dfs[coin].keys()])

                        for index, column in enumerate(columns):
                            parsed_row[column] = r[index]

                        if parsed_row:
                            parsed[coin].append(parsed_row)
        parsed['dolar'].reverse()
        parsed['euro'].reverse()
        return parsed

    def write_intermediate_panel(self, rows, intermediate_panel_path):
        """
        Escribe el panel intermedio.

        Parameters
        ----------
        rows: Iterable
        """
        header = [
            'indice_tiempo',
            'coin',
            'entity',
            'channel',
            'flow',
            'hour',
            'value'
        ]

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
                'tce-intermediate-panel.csv',
                converters={
                    'serie_tiempo': lambda _: _,
                    'coin': lambda _: str(_),
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
        _parsed = (
            [p for p in parsed['dolar']] + [p for p in parsed['euro']]
        )

        intermediate_panel_data = self.get_intermediate_panel_data_from_parsed(
            _parsed
        )
        self.write_intermediate_panel(intermediate_panel_data, self.intermediate_panel_path)

    def parse_contents(self, contents, start_date, end_date):
        """
        Retorna un diccionario que tiene como clave cada moneda
        y como valor una lista con un diccionario que tiene los
        contenidos parseados.

        Parameters
        ----------
        contents: Iterable
            Lista de diccionarios en la que cada diccionario tiene:
            string con nombre de cada moneda como clave, string con cada html
            como valor
        start_date : date
            Fecha de inicio que toma como referencia el scraper
        end_date : date
            fecha de fin que va a tomar como referencia el scraper
        entities : Dict
            Diccionario que contiene el nombre de los bancos
        """
        parsed_contents = []
        parsed_contents = {'dolar': [], 'euro': []}

        for content in contents:
            for k, v in content.items():
                single_date = content[k].get('indice_tiempo')
                day_content = content[k].get('content')
                parsed = self.get_parsed(single_date, k, self.entities)
                try:
                    parsed_day = self.parse_content(
                        day_content, single_date, k, self.entities
                    )
                    for r in parsed_day:
                        parsed_contents[k].append(r)
                except:
                    parsed_contents[k].append(parsed)

        return parsed_contents

    def parse_content(self, content, single_date, coin, entities):
        """
        Parsea el contenido y agrega los registros a un diccionario,
        retornando un iterable con el diccionario.

        Parameters
        ----------
        content: str
            Html de la moneda
        start_date : date
            Fecha de inicio que toma como referencia el scraper
        end_date : date
            fecha de fin que va a tomar como referencia el scraper
        coin : str
            Nombre de la moneda
        entities : Dict
            Diccionario que contiene el nombre de los bancos
        """
        soup = BeautifulSoup(content, "html.parser")
        try:
            table = soup.find(
                class_='table table-BCRA table-bordered table-hover ' +
                    'table-responsive'
            )
            parsed_contents = []
            result = {}
            parsed = self.get_parsed(single_date, coin, entities)

            if not table:
                parsed_contents.append(parsed)
                return parsed_contents

            body = table.find('tbody')

            if not body:
                parsed_contents.append(parsed)
                return parsed_contents

            for k, v in entities.items():
                if body.find('td', text=re.compile(v)):
                    row = body.find('td', text=re.compile(v)).parent
                    cols = row.find_all('td')
                    parsed[
                        'indice_tiempo'
                        ] = single_date
                    parsed[
                        f'tc_ars_{coin}_{k}_mostrador_compra_11hs'
                        ] =\
                        (cols[1].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_mostrador_compra_13hs'
                        ] =\
                        (cols[5].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_mostrador_compra_15hs'
                        ] =\
                        (cols[9].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_electronico_compra_11hs'
                        ] =\
                        (cols[3].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_electronico_compra_13hs'
                        ] =\
                        (cols[7].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_electronico_compra_15hs'
                        ] =\
                        (cols[11].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_mostrador_venta_11hs'
                        ] =\
                        (cols[2].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_mostrador_venta_13hs'
                        ] =\
                        (cols[6].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_mostrador_venta_15hs'
                        ] =\
                        (cols[10].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_electronico_venta_11hs'
                        ] =\
                        (cols[4].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_electronico_venta_13hs'
                        ] =\
                        (cols[8].text.strip())
                    parsed[
                        f'tc_ars_{coin}_{k}_electronico_venta_15hs'
                        ] =\
                        (cols[12].text.strip())
                result.update(parsed)
            parsed_contents.append(result)
            return parsed_contents
        except:
            parsed_contents.append(parsed)
            return parsed_contents

    def get_parsed(self, day, coin, entities):
        parsed = {}
        for k, v in entities.items():
            parsed[
                'indice_tiempo'
                ] = day
            parsed[
                f'tc_ars_{coin}_{k}_mostrador_compra_11hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_mostrador_compra_13hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_mostrador_compra_15hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_electronico_compra_11hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_electronico_compra_13hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_electronico_compra_15hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_mostrador_venta_11hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_mostrador_venta_13hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_mostrador_venta_15hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_electronico_venta_11hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_electronico_venta_13hs'
                ] = ''
            parsed[
                f'tc_ars_{coin}_{k}_electronico_venta_15hs'
                ] = ''
        return parsed


    def _preprocess_rows(self, parsed):
        parsed['dolar'] = self.preprocess_rows(
                parsed['dolar']
                )
        parsed['euro'] = self.preprocess_rows(parsed['euro'])

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
                    if row[k] == '':
                        preprocessed_row[k] = None
                    else:
                        preprocessed_row[k] = (
                                    Decimal((row[k]).replace(',', '.'))
                                    if isinstance(row[k], str)
                                    else row[k]
                                )

            preprocessed_rows.append(preprocessed_row)

        return preprocessed_rows
