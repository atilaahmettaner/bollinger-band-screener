from __future__ import annotations
from typing import Set

ALLOWED_TIMEFRAMES: Set[str] = {"5m", "15m", "1h", "4h", "1D", "1W", "1M"}
EXCHANGE_SCREENER = {
    "all": "crypto",
    "huobi": "crypto",
    "kucoin": "crypto",
    "coinbase": "crypto",
    "gateio": "crypto",
    "binance": "crypto",
    "bitfinex": "crypto",
    "bybit": "crypto",
    "okx": "crypto",
    "bist": "turkey",
    "nasdaq": "america",
}
COINLIST_DIR = 'coinlist'


def sanitize_timeframe(tf: str, default: str = "5m") -> str:
    if not tf:
        return default
    tfs = tf.strip()
    return tfs if tfs in ALLOWED_TIMEFRAMES else default


def sanitize_exchange(ex: str, default: str = "kucoin") -> str:
    if not ex:
        return default
    exs = ex.strip().lower()
    return exs if exs in EXCHANGE_SCREENER else default
