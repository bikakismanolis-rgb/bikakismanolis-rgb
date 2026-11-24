"""Στρατηγική: ακολουθούμε την τάση, με μέγεθος θέσης αντίστροφο της μεταβλητότητας.

Κανόνας: κρατάμε ένα εμπόρευμα μόνο όταν η τιμή του είναι πάνω από τον κινητό μέσο
200 ημερών. Όσο πιο "νευρικό" είναι, τόσο μικρότερη η θέση. Ό,τι δεν επενδύεται μένει μετρητά.
Μόνο αγορές (long), ποτέ μόχλευση, ποτέ short.
"""
import numpy as np
import pandas as pd

from .config import Settings


def target_weights(prices: pd.DataFrame, s: Settings) -> pd.DataFrame:
    """Βάρη-στόχοι για κάθε ημέρα, υπολογισμένα ΜΟΝΟ με δεδομένα έως και εκείνη την ημέρα."""
    rets = prices.pct_change(fill_method=None)
    sma = prices.rolling(s.trend_window, min_periods=s.trend_window).mean()
    in_trend = prices > sma
    vol = rets.rolling(s.vol_window, min_periods=s.vol_window).std() * np.sqrt(252)

    n_active = in_trend.sum(axis=1).replace(0, np.nan)
    # κάθε ενεργή θέση παίρνει ίσο μερίδιο του "προϋπολογισμού ρίσκου"
    raw = (s.target_vol / np.sqrt(n_active)).to_frame().values / vol
    w = raw.where(in_trend & vol.gt(0), 0.0).fillna(0.0).clip(upper=s.max_weight)

    gross = w.sum(axis=1)
    scale = (s.max_gross / gross).clip(upper=1.0).fillna(1.0)
    return w.mul(scale, axis=0)


def latest_weights(prices: pd.DataFrame, s: Settings) -> pd.Series:
    return target_weights(prices, s).iloc[-1]
