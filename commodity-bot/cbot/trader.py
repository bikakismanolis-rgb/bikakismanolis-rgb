"""Ένας κύκλος συναλλαγών: υπολόγισε στόχους, έλεγξε ρίσκο, στείλε εντολές."""
import math

import pandas as pd

from .broker import Broker
from .config import Settings
from .strategy import latest_weights


def equity(broker: Broker, last: pd.Series) -> float:
    return broker.cash() + sum(n * last[sym] for sym, n in broker.positions().items())


def run_cycle(broker: Broker, prices: pd.DataFrame, s: Settings) -> list:
    """Επιστρέφει λίστα με (σύμβολο, τεμάχια, τιμή) που εκτελέστηκαν."""
    last = prices.ffill().iloc[-1]
    state = broker.state
    eq = equity(broker, last)
    state["peak_equity"] = max(state["peak_equity"], eq)
    done = []

    # kill switch: αν χάσαμε πάνω από το όριο, πουλάμε τα πάντα και σταματάμε
    if not state["halted"] and eq < state["peak_equity"] * (1 - s.max_drawdown):
        state["halted"] = True
    if state["halted"]:
        for sym, n in broker.positions().items():
            broker.order(sym, -n, last[sym])
            done.append((sym, -n, last[sym]))
        return done

    target = latest_weights(prices, s)
    held = broker.positions()
    deltas = {}
    for sym in prices.columns:
        px = last[sym]
        if not px or math.isnan(px):
            continue
        cur = held.get(sym, 0)
        want = math.floor(target[sym] * eq / px)
        # μην κάνεις μικρο-συναλλαγές, εκτός αν πρόκειται για πλήρη έξοδο
        if abs(want - cur) * px < s.rebalance_band * eq and not (want == 0 and cur > 0):
            continue
        if want != cur:
            deltas[sym] = want - cur

    # πρώτα οι πωλήσεις για να ελευθερωθούν μετρητά
    for sym, d in sorted(deltas.items(), key=lambda kv: kv[1]):
        px = last[sym]
        if d > 0:
            affordable = math.floor(broker.cash() / (px * (1 + s.cost_bps / 1e4)))
            d = min(d, affordable)
        if d:
            broker.order(sym, d, px)
            done.append((sym, d, px))
    return done
