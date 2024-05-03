import argparse
from typing import List

import time

import pandas as pd

from src.exchanges.mexc.futures.api_futures import MexcFutures
from src.exchanges.mexc.futures.ws_client import MexcWsClient, KlineSubscribeChannel


def handle(message):
    print(message)


coins = {}


def get_leveraged_symbols(data: List[dict], leverage_filter: int = 100) -> List[str]:
    global coins
    leveraged_symbols = []
    for d in data:
        if d["symbol"].lower()[-4:] == "usdt":
            if d["maxLeverage"] >= leverage_filter:
                leveraged_symbols.append(d["symbol"])
                coins[d["symbol"]] = {
                    "contract_equal_to_coin": d["contractSize"],
                    "leverage": d["maxLeverage"],
                }

    return leveraged_symbols


def filter_market_data(data: List[dict], symbols_filter: list):
    global coins
    for d in data:
        if d["symbol"] in symbols_filter:
            coins[d["symbol"]]["last_price"] = d["lastPrice"]


def calclulate_data_for_coins():
    global coins
    # primero multiplicamos la minima cantidad de monedas por el precio. Para esto usamos la llave
    # "contract_equal_to_coin" que es el mínimo de monedas y obtener el valor de entrada
    for k in coins.keys():
        coins[k]["min_value"] = (
            coins[k]["contract_equal_to_coin"] * coins[k]["last_price"]
        )
        coins[k]["min_margin"] = round(coins[k]["min_value"] / coins[k]["leverage"], 4)


def get_tradeable_symbols(filter_price, volaility_filter) -> List[str]:
    global coins
    tradeable_symbols = []
    for k in coins.keys():
        if (
            coins[k]["min_margin"] <= filter_price
            and coins[k]["volatility"] >= volaility_filter
        ):
            tradeable_symbols.append(k)
    return tradeable_symbols


def get_actual_volatility(client: MexcFutures, lookback_bars: int):
    """Obtiene la volatilidad de las monedas tomando el promedio de las ultima cantidad
    de velas que ingresemos y validando que cumplan el mínimo de volatilidad"""
    global coins
    for k in coins.keys():
        data = client.get_klines(symbol=k, interval_minutes=5, limit=lookback_bars)
        coins[k]["volatility"] = get_volatility(data)
        time.sleep(2)


def get_volatility(data: pd.DataFrame) -> float:
    """Calcula la voalatilidad de la data que es retornada en un dataframe"""
    df = data
    df["volatility"] = round(abs(df["high"] - df["low"]) * 100 / df["low"], 4)
    return round(df["volatility"].mean(), 2)


def filer_by_minimum_margin(min_margin):
    global coins
    coins_with_min_margin = {}
    for k in coins.keys():
        if coins[k]["min_margin"] <= min_margin:
            coins_with_min_margin[k] = coins[k]
    return coins_with_min_margin


def msg(symbol: str, leverage: int, volatilidad: float, min_margin: float) -> str:
    msg = f"{'*' * 50}\nSymbol: {symbol.upper()}\nApalancamiento: {leverage}\nvolatilidad:  {volatilidad}%\nMargen Mínimo: ${min_margin}\n{'*' * 50}"
    return msg


def run():
    global coins
    parser = argparse.ArgumentParser(description="Excaneador de monedas")
    parser.add_argument('-c', '--capital', type=float, help='Capital de tu cuenta')
    parser.add_argument('-s', '--estrategia', type=str, help='Estrategia a usar', choices=["cco", "ccd"], default="ccd")
    parser.add_argument('-l', '--apalancamiento', type=int, default=100, required=False, help='Apalancamiento mínimo a buscar. Default 100')
    parser.add_argument('-k', '--klines', type=int, default=5, required=False, help='cantidad de velas a ver hacia atrás para medir la volatilidad. Default 5')
    parser.add_argument('-v','--volatilidad', type=float, default=1.0, required=False, help='Volatilidad mínima promedio en las últimas velas. Default 1%')
    args = parser.parse_args()

    try:
        if args.capital is None:
            raise ValueError("Debes ingresar un capital. Usa <<python app.py -c 'capital'>>")
        capital = args.capital

        if args.estrategia.lower() == "ccd":
            price_filter = round((0.05 * capital) / 100, 2)
        else:
            price_filter = round((0.1 * capital) / 100, 2)

        leverage = args.apalancamiento
        velas = args.klines
        volatilidad = args.volatilidad

        print("Conectando con exchange ...")
        client = MexcFutures(api_key="", api_secret="")
        print("Conexión establecida, obteniendo symbols tradeables ...")
        all_symbols_info = client.get_all_contracts_info()
        print(f"Todos los symbols: {len(all_symbols_info)}")
        leveraged_symbols = get_leveraged_symbols(all_symbols_info, leverage)
        print(f"Monedas que cumple apalancamiento >= {leverage}: {len(leveraged_symbols)}")
        all_symbols_market_info = client.get_all_contracts_market_data()
        filter_market_data(data=all_symbols_market_info, symbols_filter=leveraged_symbols)
        calclulate_data_for_coins()
        coins = filer_by_minimum_margin(min_margin=price_filter)
        print(f"Monedas que cumplen con margen mínimo: {len(coins)}")
        print("Buscando volatilidad ...")
        get_actual_volatility(client=client, lookback_bars=velas)
        tradeable_symbols = get_tradeable_symbols(price_filter, volatilidad)
        print("Monedas tradeables")
        if len(tradeable_symbols) > 0:
            for s in tradeable_symbols:
                print(
                    msg(
                        symbol=s,
                        leverage=coins[s]["leverage"],
                        volatilidad=coins[s]["volatility"],
                        min_margin=coins[s]["min_margin"],
                    )
                )
        else:
            print("No hay symbols tradeables por el momento")

    except ValueError as ve:
        print(ve)

"""
    
    # klines = client.get_klines(interval_minutes=5, symbol="Btc")
    # print(klines)
    # client = MexcWsClient(api_key="", api_secret="", need_login=False)
    # client.build()
    # client.subscribe([btc_5min_kline], handle)
"""

if __name__ == "__main__":
    run()
