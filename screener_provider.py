from __future__ import annotations
from typing import List, Dict, Any, Optional


def fetch_screener_indicators(exchange: str, symbols: List[str], limit: Optional[int] = None, cookies=None) -> List[Dict[str, Any]]:
    """
    Minimal wrapper around tradingview_screener.Query to fetch required indicator columns.
    Returns a list of rows: { 'symbol': 'EXCHANGE:PAIR', 'indicators': { ... } }.
    """
    try:
        from tradingview_screener import Query
    except Exception as e:
        # Defer import errors to caller in a controlled way
        raise ImportError("tradingview-screener is not installed. Please add it to requirements.txt and install.") from e

    # Market mapping: for centralized exchanges we use 'crypto'
    market = 'crypto'
    cols = ['open', 'close', 'SMA20', 'BB.upper', 'BB.lower', 'EMA50', 'RSI', 'volume']

    q = (Query()
         .set_markets(market)
         # set_tickers expects varargs, not a list
         .set_tickers(*symbols)
         .select(*cols))

    if limit:
        q = q.limit(limit)

    total, df = q.get_scanner_data(cookies=cookies)

    rows: List[Dict[str, Any]] = []
    if df is None or df.empty:
        return rows

    for _, row in df.iterrows():
        symbol = row.get('ticker')  # DataFrame usually includes 'ticker'
        indicators = {
            'open': row.get('open'),
            'close': row.get('close'),
            'SMA20': row.get('SMA20'),
            'BB.upper': row.get('BB.upper'),
            'BB.lower': row.get('BB.lower'),
            'EMA50': row.get('EMA50'),
            'RSI': row.get('RSI'),
            'volume': row.get('volume'),
        }
        rows.append({'symbol': symbol, 'indicators': indicators})

    return rows
