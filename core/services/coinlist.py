from __future__ import annotations
import os
from typing import List
from core.utils.validators import COINLIST_DIR


def load_symbols(exchange: str) -> List[str]:
    path = os.path.join(COINLIST_DIR, f"{exchange}.txt")
    try:
        with open(path) as f:
            content = f.read()
        symbols = [line for line in content.split('\n') if line]
        return symbols
    except FileNotFoundError:
        return []
