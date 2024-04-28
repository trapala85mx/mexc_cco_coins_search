def parse_symbol(symbol: str) -> str:
    # verificamos si se envió el symbol si no arrojamos error
    if not symbol or len(symbol) == 0:
        raise ValueError("No se envió moneda")

    if "_" in symbol:
        symbol = symbol.replace("_","")
    # parseamos el symbol a como lo usa mexc BTC_USDT
    if symbol.lower()[-4:] == "usdt":
        ticker = symbol[:-4]
        symbol = f"{ticker.upper()}_USDT"

    else:
        symbol = f"{symbol.upper()}_USDT"


    return symbol