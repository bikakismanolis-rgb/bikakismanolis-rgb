"""Backtest: πώς θα είχε πάει η στρατηγική στο παρελθόν, με κόστη συναλλαγών."""
import numpy as np
import pandas as pd

from .config import Settings
from .strategy import target_weights


def run_backtest(prices: pd.DataFrame, s: Settings) -> pd.DataFrame:
    rets = prices.pct_change(fill_method=None).fillna(0.0)
    w = target_weights(prices, s)

    # αναπροσαρμογή κάθε N συνεδριάσεις, ενδιάμεσα κρατάμε τα ίδια βάρη
    is_rebal = np.arange(len(w)) % s.rebalance_every == 0
    held = w.where(pd.Series(is_rebal, index=w.index), np.nan).ffill().fillna(0.0)

    # σήμα στο κλείσιμο της ημέρας t, εκτέλεση στο κλείσιμο t+1, απόδοση από t+2
    live = held.shift(2).fillna(0.0)
    turnover = live.diff().abs().sum(axis=1).fillna(0.0)
    strat = (live * rets).sum(axis=1) - turnover * s.cost_bps / 1e4

    # σημείο αναφοράς: ίσα βάρη σε ό,τι διαπραγματεύεται, αγορά και διακράτηση
    avail = prices.notna()
    bench = (rets.where(avail.shift(1, fill_value=False), 0.0)).sum(axis=1) / avail.sum(axis=1).clip(lower=1)

    return pd.DataFrame({"strategy": strat, "buy_hold": bench, "exposure": live.sum(axis=1)})


def metrics(daily: pd.Series) -> dict:
    eq = (1 + daily).cumprod()
    years = len(daily) / 252
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = daily.std() * np.sqrt(252)
    dd = (eq / eq.cummax() - 1).min()
    return {
        "CAGR": cagr,
        "Volatility": vol,
        "Sharpe": (daily.mean() * 252 / vol) if vol > 0 else 0.0,
        "MaxDrawdown": dd,
        "Total": eq.iloc[-1] - 1,
    }
