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
        if d['symbol'].lower()[-4:] == "usdt":
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
        if coins[k]["min_margin"] <= filter_price and coins[k]['volatility'] >= volaility_filter:
            tradeable_symbols.append(k)
    return tradeable_symbols


def get_actual_volatility(client: MexcFutures, lookback_bars: int):
    """Obtiene la volatilidad de las monedas tomando el promedio de las ultima cantidad
    de velas que ingresemos y validando que cumplan el mínimo de volatilidad"""
    global coins
    for k in coins.keys():
        data = client.get_klines(symbol=k, interval_minutes=5, limit=lookback_bars)
        coins[k]['volatility'] = get_volatility(data)
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


def run():
    global coins
    leverage = 125
    capital = 30
    price_filter = round((0.1 * capital) / 100, 2)
    volatilidad = 1  # En porcentaje
    velas = 5  # la cantidad de velas que usaremos para revisar la volatilidad

    btc_5min_kline = KlineSubscribeChannel(symbol="BTC_USDT", interval="Min5")
    print("Conexion Cliente")
    client = MexcFutures(api_key="", api_secret="")
    print("extaccion informacion contratos")
    # Traer toda  la info de todas las moendas
    all_symbols_info = client.get_all_contracts_info()
    print("Todos los symbols", len(all_symbols_info))

    # Nos quedamos con las monedas que tengan un apalancamiento mayor o igual al establecido
    leveraged_symbols = get_leveraged_symbols(all_symbols_info, leverage)
    print("Symbols con  leverage >=  ", leverage, ":", len(leveraged_symbols))

    # Traemos toda la información de mercado para todas las moendas
    all_symbols_market_info = client.get_all_contracts_market_data()

    # Obtenemos el precio más actual de las monedas que cumplen el apalancamiento
    filter_market_data(data=all_symbols_market_info, symbols_filter=leveraged_symbols)

    # De la información obtenida calculamos el precio de entrada para obtener el margen mínimo necesario
    calclulate_data_for_coins()

    # filtramos moendas por minimo margen necesario
    coins = filer_by_minimum_margin(min_margin=price_filter)
    print(f"Symbols que cumplen el mínimo margen de ${price_filter}: {len(coins)}")

    # Obtener las velas de cada moneda y obtener la volatilidad de cada una
    get_actual_volatility(client=client, lookback_bars=velas)

    tradeable_symbols = get_tradeable_symbols(price_filter, volatilidad)
    print(f"Symbols tradeables que cumplen apalancamiento >= {leverage}, margen minimo <= {price_filter} y "
          f"volatilidad >= {volatilidad}% en las últimas {velas} velas")
    print(tradeable_symbols)
    #print(coins)
"""
    
    # klines = client.get_klines(interval_minutes=5, symbol="Btc")
    # print(klines)
    # client = MexcWsClient(api_key="", api_secret="", need_login=False)
    # client.build()
    # client.subscribe([btc_5min_kline], handle)
"""

if __name__ == "__main__":
    run()
