#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from csv import DictWriter
from datetime import date
from json import JSONDecodeError
import json

import click

from bcra_scraper.exceptions import InvalidConfigurationError

from bcra_scraper.scraper import BCRALiborScraper, BCRAExchangeRateScraper
from bcra_scraper.scraper import BCRASMLScraper


# TODO: test me!
def write_tasas_libor(file_name, header, rows):
    with open(file_name, 'w') as archivo:
        writer = DictWriter(archivo, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def get_default_start_date():
    today = date.today()

    return f'{today.day}/{today.month}/{today.year}'


def get_default_end_date():
    today = date.today()

    return f'{today.day}/{today.month}/{today.year}'


def read_config(file_path, command):
    try:
        with open(file_path) as config_data:
            return json.load(config_data)[command]
    except JSONDecodeError:
        raise InvalidConfigurationError(
            "El formato del archivo de configuración es inválido"
        )


def validate_url_config(config):
    if 'url' not in config:
        raise InvalidConfigurationError("La clave url no existe")


# def validate_url_has_value(config):
#     url = config['url'].split(':')
#     if url[0] != 'http':
#         raise InvalidConfigurationError("La url no es válida")


def validate_url_has_value(config):
    if config['url'] == '':
        raise InvalidConfigurationError("La url no es válida")


def validate_libor_rates_config(config):
    if 'rates' not in config:
        raise InvalidConfigurationError("La clave rates no existe")


def validate_libor_rates_has_values(config):
    rates = config.get('rates', {})
    if rates == {}:
        raise InvalidConfigurationError("No existen valores para rates")


def validate_coins_key_config(config):
    if 'coins' not in config:
        raise InvalidConfigurationError("La clave coins no existe")


def validate_coins_key_has_values(config):
    coins = config.get('coins', {})
    if coins == {}:
        raise InvalidConfigurationError("No existen valores para coins")


@click.group()
@click.pass_context
def cli(ctx):
    pass


# TODO: validar q no se ingrese solo end_date
# TODO: validar q end_date >= start_date
@cli.command()
@click.option(
    '--start-date',
    default=get_default_start_date,
    type=click.DateTime(formats=['%d/%m/%Y']),
    )
@click.option(
    '--end-date',
    default=get_default_end_date,
    type=click.DateTime(formats=['%d/%m/%Y']),
    )
@click.option(
    '--config',
    default='config.json',
    type=click.Path(exists=True),
    )
@click.option(
    '--use-intermediate-panel',
    default=False,
    is_flag=True,
    help=('Use este flag para forzar la lectura de datos desde un'
          'archivo intermedio')
)
@click.pass_context
def libor(ctx, start_date, end_date, config, use_intermediate_panel,
          *args, **kwargs):

    start_date = date(start_date.year, start_date.month, start_date.day)
    end_date = date(end_date.year, end_date.month, end_date.day)

    try:
        config = read_config(file_path=config, command=ctx.command.name)

        validate_url_config(config)
        validate_url_has_value(config)
        validate_libor_rates_config(config)
        validate_libor_rates_has_values(config)

        scraper = BCRALiborScraper(
            url=config.get('url'),
            rates=config.get('rates'),
            use_intermediate_panel=use_intermediate_panel
        )

        parsed = scraper.run(start_date, end_date)

        if parsed:
            csv_name = 'tasas-libor.csv'

            # csv_header = ['indice_tiempo', '30', '60', '90', '180', '360']
            processed_header = scraper.preprocess_header(scraper.rates)

            write_tasas_libor(csv_name, processed_header, parsed)
        else:
            click.echo("No se encontraron resultados")
    except InvalidConfigurationError as err:
        click.echo(err)


@cli.command()
@click.option(
    '--start-date',
    default=get_default_start_date,
    type=click.DateTime(formats=['%d/%m/%Y']),
    )
@click.option(
    '--end-date',
    default=get_default_end_date,
    type=click.DateTime(formats=['%d/%m/%Y']),
    )
@click.option(
    '--config',
    default='config.json',
    type=click.Path(exists=True),
    )
@click.option(
    '--use-intermediate-panel',
    default=False,
    is_flag=True,
    help=('Use este flag para forzar la lectura de datos desde un'
          'archivo intermedio')
)
@click.pass_context
def exchange_rates(ctx, start_date, end_date, config, use_intermediate_panel):

    try:
        config = read_config(file_path=config, command=ctx.command.name)
        validate_url_config(config)
        validate_url_has_value(config)
        validate_coins_key_config(config)
        validate_coins_key_has_values(config)

        scraper = BCRAExchangeRateScraper(
            url=config.get('url'),
            coins=config.get('coins'),
            use_intermediate_panel=use_intermediate_panel
        )
        parsed = scraper.run(start_date, end_date)

        if parsed:
            coins = config.get('coins')

            csv_name = 'tipos-pase-usd-series.csv'
            csv_header = ['indice_tiempo']
            csv_header.extend([v for v in coins.keys()])

            write_tasas_libor(csv_name, csv_header, parsed['tp_usd'])

            csv_name = 'tipos-cambio-local-series.csv'
            csv_header = ['indice_tiempo']
            csv_header.extend([v for v in coins.keys()])

            write_tasas_libor(csv_name, csv_header, parsed['tc_local'])

        else:
            click.echo("No se encontraron resultados")

    except InvalidConfigurationError as err:
        click.echo(err)


@cli.command()
@click.option(
    '--start-date',
    default=get_default_start_date,
    type=click.DateTime(formats=['%d/%m/%Y']),
)
@click.option(
    '--end-date',
    default=get_default_end_date,
    type=click.DateTime(formats=['%d/%m/%Y']),
)
@click.option(
    '--config',
    default='config.json',
    type=click.Path(exists=True),
)
@click.pass_context
def sml(ctx, config, start_date, end_date):

    try:
        config = read_config(file_path=config, command=ctx.command.name)
        validate_url_config(config)
        validate_url_has_value(config)
        validate_coins_key_config(config)
        validate_coins_key_has_values(config)

        scraper = BCRASMLScraper(
            url=config.get('url'),
            coins=config.get('coins'), use_intermediate_panel=False
        )
        scraper.run(start_date, end_date)

    except InvalidConfigurationError as err:
        click.echo(err)
