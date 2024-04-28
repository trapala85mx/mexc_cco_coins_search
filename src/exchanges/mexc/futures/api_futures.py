import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

import pandas as pd
import requests

from src.exchanges.mexc.utils.parsers import parse_symbol


@dataclass(kw_only=True)
class MexcFutures:
    api_key: str
    api_secret: str
    base_url: str = field(init=False, default="https://contract.mexc.com/")
    timeframes = {1: "Min1", 5: "Min5", 15: "Min15"}

    def get_klines(
        self,
        symbol: str,
        interval_minutes: int,
        limit: int = 200,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> pd.DataFrame:
        symbol = parse_symbol(symbol)

        # Armamos los datos para el Request
        endpoint = f"api/v1/contract/kline/{symbol}"
        method = "GET"

        params = {
            "interval": self.timeframes[interval_minutes],
            "start": self._calcular_start_timestamp(
                limit=limit + 1, interval_minutes=interval_minutes
            ),
        }

        # Hacemos la request
        response = requests.request(
            method=method, url=self.base_url + endpoint, params=params
        )

        # Verificamos sea un 2XX
        if not str(response.status_code).startswith("2"):
            raise requests.exceptions.RequestException

        response = response.json()["data"]

        # Verificamos qintegridad de la data
        if not len(response["time"]) >= limit and len(response["time"]) > 0:
            raise ValueError("No se extrajeron las velas necesarias")

        if len(response["time"]) == 0:
            raise ValueError("No se obtuvieron datos")

        # Convertimos la data en DataFrame
        data = {
            "open_time": response["time"],
            "open": response["open"],
            "close": response["close"],
            "high": response["high"],
            "low": response["low"],
            "volume": response["vol"],
            "amount": response["amount"],
        }

        df = pd.DataFrame(data)
        df = df.iloc[:-1]

        # Convertimos el open_time en fecha
        df["open_time"] = pd.to_datetime(df["open_time"], unit="s")

        return df

    def _calcular_start_timestamp(self, limit: int, interval_minutes: int):
        # Obtenemos la hora actual en formato Unix timestamp en segundos
        hora_actual = int(time.time())

        # Convertimos la temporalidad a segundos
        temporalidad_segundos = interval_minutes * 60

        # Calculamos la diferencia de tiempo basada en la temporalidad
        tiempo_total = limit * temporalidad_segundos

        # Calculamos la fecha de inicio restando el tiempo total de la hora actual
        fecha_inicio = datetime.fromtimestamp(hora_actual - tiempo_total)

        # Convertimos la fecha de inicio a timestamp en segundos
        fecha_inicio_timestamp = int(fecha_inicio.timestamp())

        return fecha_inicio_timestamp

    def get_all_contracts_info(self) -> List[dict]:
        endpoint = "api/v1/contract/detail"
        method = "GET"

        # Hacemos la request
        response = requests.request(method, url=self.base_url + endpoint)

        # Verificamos sea un 2XX
        if not str(response.status_code).startswith("2"):
            raise requests.exceptions.RequestException

        response = response.json()["data"]

        return response

    def get_all_contracts_market_data(self) -> List[dict]:
        endpoint = "api/v1/contract/ticker"
        method = "GET"

        # Hacemos la request
        response = requests.request(method, url=self.base_url + endpoint)

        # Verificamos sea un 2XX
        if not str(response.status_code).startswith("2"):
            raise requests.exceptions.RequestException

        response = response.json()["data"]

        return response
