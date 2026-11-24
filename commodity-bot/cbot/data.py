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


def clean_prices(prices: pd.DataFrame, spike: float = 0.15, max_move: float = 0.25) -> pd.DataFrame:
    """Διορθώνει τα λάθη των δωρεάν δεδομένων.

    1. Μεμονωμένες λάθος τιμές: άλμα πάνω από 15% που αναιρείται σχεδόν πλήρως την επόμενη μέρα.
    2. Αλλαγές κλίμακας (π.χ. reverse split που δεν έχει προσαρμοστεί): ημερήσια κίνηση
       πάνω από 25% δεν έχει συμβεί ποτέ πραγματικά σε αυτά τα προϊόντα, οπότε τη
       θεωρούμε ασυνέχεια και ξαναχτίζουμε τη σειρά χωρίς αυτήν.
    Οι πιο πρόσφατες τιμές μένουν ίδιες με τις πραγματικές.
    """
    p = prices.copy()
    for _ in range(3):
        f = p.ffill()
        r = f / f.shift(1) - 1
        round_trip = f.shift(-1) / f.shift(1) - 1
        bad = (r.abs() > spike) & (round_trip.abs() < r.abs() / 4)
        if not bad.any().any():
            break
        p = p.mask(bad)
    f = p.ffill()
    r = f.pct_change(fill_method=None)
    r = r.mask(r.abs() > max_move, 0.0)
    growth = (1 + r.fillna(0.0)).cumprod()
    adj = growth / growth.iloc[-1] * f.iloc[-1]
    return adj.where(f.notna())


def load_prices(symbols, refresh: bool = False, max_age_hours: float = 12, clean: bool = True) -> pd.DataFrame:
    """Επιστρέφει πίνακα τιμών (στήλη ανά σύμβολο). Κατεβάζει ξανά αν η cache είναι παλιά."""
    DATA_DIR.mkdir(exist_ok=True)
    out = {}
    for sym in symbols:
        path = DATA_DIR / f"{sym}.csv"
        stale = not path.exists() or (time.time() - path.stat().st_mtime) > max_age_hours * 3600
        if refresh or stale:
            fetch_symbol(sym).to_csv(path, header=True)
        out[sym] = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
    prices = pd.DataFrame(out).sort_index()
    return clean_prices(prices) if clean else prices
