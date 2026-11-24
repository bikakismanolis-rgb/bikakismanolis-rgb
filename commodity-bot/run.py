#!/usr/bin/env python3
"""Χρήση:
  python run.py backtest          ιστορική δοκιμή της στρατηγικής
  python run.py signals           τι θα κρατούσε σήμερα η στρατηγική
  python run.py paper             ένας κύκλος εικονικών συναλλαγών (τρέξ' το μία φορά τη μέρα)
  python run.py status            κατάσταση του εικονικού χαρτοφυλακίου
  python run.py reset-halt        επανενεργοποίηση μετά από kill switch
"""
import sys
from datetime import date
from pathlib import Path

from cbot.backtest import metrics, run_backtest
from cbot.broker import PaperBroker
from cbot.config import SETTINGS, UNIVERSE
from cbot.data import load_prices
from cbot.strategy import latest_weights
from cbot.trader import equity, run_cycle

STATE = Path(__file__).resolve().parent / "state" / "paper.json"


def cmd_backtest(prices):
    res = run_backtest(prices, SETTINGS)
    res = res.loc[prices.index[SETTINGS.trend_window]:]
    print(f"Περίοδος: {res.index[0].date()} έως {res.index[-1].date()}  |  "
          f"κόστος {SETTINGS.cost_bps:.0f} bps ανά συναλλαγή\n")
    print(f"{'':14}{'Στρατηγική':>12}{'Buy & hold':>12}")
    ms, mb = metrics(res["strategy"]), metrics(res["buy_hold"])
    labels = {"CAGR": "Ετήσια απόδ.", "Volatility": "Μεταβλητότ.", "Sharpe": "Sharpe",
              "MaxDrawdown": "Μέγ. πτώση", "Total": "Σύνολο"}
    for k, lab in labels.items():
        fmt = "{:>12.2f}" if k == "Sharpe" else "{:>12.1%}"
        print(f"{lab:14}" + fmt.format(ms[k]) + fmt.format(mb[k]))
    print(f"\nΜέση έκθεση στην αγορά: {res['exposure'].mean():.0%}")
    print("\nΑνά ημερολογιακό έτος (στρατηγική / buy & hold):")
    yearly = (1 + res[["strategy", "buy_hold"]]).groupby(res.index.year).prod() - 1
    for y, row in yearly.iterrows():
        print(f"  {y}: {row['strategy']:>7.1%} / {row['buy_hold']:>7.1%}")


def cmd_signals(prices):
    w = latest_weights(prices, SETTINGS)
    print(f"Σήματα με βάση το κλείσιμο {prices.index[-1].date()}:\n")
    for sym, name in UNIVERSE.items():
        mark = f"{w[sym]:6.1%}" if w[sym] > 0 else "   -  "
        print(f"  {sym:5} {name:22} {mark}")
    print(f"\n  Επενδυμένο: {w.sum():.1%}   Μετρητά: {1 - w.sum():.1%}")


def cmd_paper(prices):
    broker = PaperBroker(STATE, cost_bps=SETTINGS.cost_bps)
    trades = run_cycle(broker, prices, SETTINGS)
    eq = equity(broker, prices.ffill().iloc[-1])
    broker.state["equity_log"].append({"date": str(date.today()), "equity": round(eq, 2)})
    broker.save()
    if broker.state["halted"]:
        print("KILL SWITCH ενεργό: όλες οι θέσεις έκλεισαν, δεν γίνονται νέες συναλλαγές.")
    for sym, n, px in trades:
        print(f"  {'ΑΓΟΡΑ ' if n > 0 else 'ΠΩΛΗΣΗ'} {abs(n):>5} {sym:5} @ {px:.2f}")
    if not trades:
        print("  Καμία συναλλαγή σήμερα.")
    print(f"\nΑξία χαρτοφυλακίου: {eq:,.2f}   Μετρητά: {broker.cash():,.2f}")


def cmd_status(prices):
    broker = PaperBroker(STATE, cost_bps=SETTINGS.cost_bps)
    last = prices.ffill().iloc[-1]
    eq = equity(broker, last)
    print(f"Αξία: {eq:,.2f}   Υψηλό: {broker.state['peak_equity']:,.2f}   "
          f"Μετρητά: {broker.cash():,.2f}   Συναλλαγές: {len(broker.state['trades'])}"
          f"{'   [HALTED]' if broker.state['halted'] else ''}")
    for sym, n in broker.positions().items():
        print(f"  {sym:5} {n:>5} τεμ.  {n * last[sym]:>10,.2f}  ({n * last[sym] / eq:.1%})")


def cmd_reset_halt(_prices):
    broker = PaperBroker(STATE, cost_bps=SETTINGS.cost_bps)
    broker.state["halted"] = False
    broker.state["peak_equity"] = broker.cash()
    broker.save()
    print("Το kill switch απενεργοποιήθηκε.")


COMMANDS = {"backtest": cmd_backtest, "signals": cmd_signals, "paper": cmd_paper,
            "status": cmd_status, "reset-halt": cmd_reset_halt}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](load_prices(list(UNIVERSE)))
