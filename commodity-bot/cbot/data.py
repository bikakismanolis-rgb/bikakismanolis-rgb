"""Λήψη ημερήσιων τιμών (προσαρμοσμένο κλείσιμο) από το Yahoo Finance, με τοπική cache."""
from pathlib import Path
import time

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def fetch_symbol(symbol: str, years: int = 20) -> pd.Series:
    r = requests.get(
        URL.format(symbol=symbol),
        params={"range": f"{years}y", "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    idx = pd.to_datetime(result["timestamp"], unit="s").normalize()
    s = pd.Series(result["indicators"]["adjclose"][0]["adjclose"], index=idx, name=symbol, dtype=float)
    return s[~s.index.duplicated(keep="last")].dropna()


def load_prices(symbols, refresh: bool = False, max_age_hours: float = 12) -> pd.DataFrame:
    """Επιστρέφει πίνακα τιμών (στήλη ανά σύμβολο). Κατεβάζει ξανά αν η cache είναι παλιά."""
    DATA_DIR.mkdir(exist_ok=True)
    out = {}
    for sym in symbols:
        path = DATA_DIR / f"{sym}.csv"
        stale = not path.exists() or (time.time() - path.stat().st_mtime) > max_age_hours * 3600
        if refresh or stale:
            fetch_symbol(sym).to_csv(path, header=True)
        out[sym] = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
    return pd.DataFrame(out).sort_index()
