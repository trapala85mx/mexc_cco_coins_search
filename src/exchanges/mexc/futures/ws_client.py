import json
import time
from typing import Optional, List
import threading
from threading import Timer

import websocket

"""
CREACIÖN DE UN CLIENTE WEBSOCKET

1. Al crear el objeto pasamos los datos:
    - key y secret (necesarios si es un stream que necesita login)
    - need_login para saber si necesita o no login
    - Una vez inicializado ejecutamos el método build que nos ayudará a la construcción de objeto que nos
        ayudará a manetener la conexión entre servidor y cliente
        
        - Creamos el objeto con el método __create_ws. Este mpetodo hace la petición al servidor para aceptar el
            protocolo websocket y retorna el objeto WebsocketApp que es un websocketprotocol con el el que enviamos
            y recibimos mensajes hacia y desde el servidor
        - Luego creamos un hilo que ejecutará el protocolo y lo mantendrá abierto. Esto lo hacemos en otro hilo para
            no interrumpir el hilo principal y poder enviar mensajes después. 
            
            - El hilo tendrá como objetivo al método _connect encargado de conectar al servidor y mantener abierto
        
        - El método build analizarpa hasta que se haya establecido la conexión a través del atributo has_connected
            para poder continuar su ejecución
        
        - Una vez conectado se mantiene la conexión abierta enviando PING al servidor cada 20 segundos (o lo que
            diga la documentación) para lo ue usaremos PING_TIMEOUT
            - Esto se hace ejecutando ell método _keep_connected que hace el llamado a un hilo Timer que se destruye
                cada "x" tiempo, en este caso PING_TIMEOUT y recibe el mismo método _keep_connected y una tupla de
                argumentos en este caso el PING_TIMMEOUT.
            - Esto hará que al destruirse el Timer se esté creando otro hilo como si estuvieramos haciendo recursion
                de hilos hacia el mismo método el cual nos permitirá estar enviando el PING
            - el método _keep_connected, como al llegar a este punto ya se debio establece la conexión con el servidor
                enviará el mensaje de acuerdo a cómo el servidor lo rqueraa
        
        - Por último, el método build retorna al objeto con el websocket abierto y en espera de enviar y recibir 
            mensajes pudiendo trabajar en el hilo principal ya que el websocket se ejcuta en otro hilo
"""


class Channel:
    def __init__(self, method: str, param: dict):
        self.method = method
        self.param = param


class KlineSubscribeChannel(Channel):
    def __init__(self, symbol: str, interval: str):
        self.method = "sub.kline"
        self.symbol = symbol
        self.interval = interval
        super().__init__(
            method=self.method,
            param={"symbol": self.symbol, "interval": self.interval},
        )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(self.method + self.symbol + self.interval)


class MexcWsClient:
    PING_TIMEOUT = 20
    WS_URL = "wss://contract.mexc.com/edge"

    def __init__(
        self,
        api_key: Optional[str] = "",
        api_secret: Optional[str] = "",
        need_login: Optional[bool] = False,
    ):
        self._api_key: str = api_key
        self._api_secret: str = api_secret
        self._need_login = need_login
        self._has_connected: bool = False
        self._ws_app = None
        self._subscribe_map = {}  # Diccionario que guarda el canal con su listener
        self._subscribed_channels = set()  # para guardar los canales suscritos

    def build(self):
        self._ws_app: websocket.WebSocketApp = self._create_wsapp()
        __thread = threading.Thread(target=self._connect)
        __thread.start()

        while not self._has_connected:
            print(f"Conectándose ... url: {self.WS_URL}")
            time.sleep(1)

        if self._need_login:
            raise NotImplementedError

        self._keep_connected(self.PING_TIMEOUT)

        return self

    def _create_wsapp(self) -> websocket.WebSocketApp:
        return websocket.WebSocketApp(
            self.WS_URL,
            on_open=self.__on_open,
            on_message=self.__on_message,
            on_error=self.__on_error,
            on_close=self.__on_close,
        )

    def _connect(self):
        try:
            self._ws_app.run_forever()

        except Exception as e:
            print(e)

    def _keep_connected(self, ping_timeout: int):
        try:
            _timer_thread = Timer(ping_timeout, self._keep_connected, (ping_timeout,))
            _timer_thread.start()
            msg = {"method": "ping"}
            self._ws_app.send(json.dumps(msg))

        except Exception as e:
            print(e)

    def __on_open(self, ws):
        print("Conexión establecida ....")
        self._has_connected = True
        self.__reconnect_status = False

    def __on_message(self, ws, message: str):
        msg = json.loads(message)
        if msg.get("channel") == "pong":
            print("Keep connected:" + message)
            return

    def __on_error(self, ws, message: str):
        pass

    def __on_close(self, ws, close_status_code: str, close_msg: str):
        pass

    def subscribe(self, channels: List[Channel], listener: callable = None):
        # asociamos el listener con su canal
        for ch in channels:
            self._subscribe_map[ch] = listener

        # agregamos el canal a los canales suscritos
        for ch in channels:
            self._subscribed_channels.add(ch)
            msg = json.dumps(ch.__dict__)
            print("send message: ", msg)
            self._ws_app.send(msg)
