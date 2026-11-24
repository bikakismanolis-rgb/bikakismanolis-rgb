#!/usr/bin/env python3
"""Χρήση:
  python run.py backtest          ιστορική δοκιμή της στρατηγικής
  python run.py signals           τάση σε όλα τα εμπορεύματα και τι θα κρατούσε σήμερα
  python run.py paper             ένας κύκλος εικονικών συναλλαγών (μία φορά τη μέρα)
  python run.py status            κατάσταση του εικονικού χαρτοφυλακίου
  python run.py reset-halt        επανενεργοποίηση μετά από kill switch (paper)
  python run.py live              Interactive Brokers: δείχνει τις εντολές ΧΩΡΙΣ να τις στείλει
  python run.py live --send       Interactive Brokers: στέλνει πραγματικά τις εντολές

Για το live: IBKR_PORT (προεπιλογή 4002 = paper Gateway), IBKR_HOST, IBKR_CLIENT_ID.
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

from cbot.backtest import metrics, run_backtest
from cbot.broker import PaperBroker
from cbot.config import SETTINGS, TRADED, UNIVERSE
from cbot.data import load_prices
from cbot.strategy import latest_weights
from cbot.trader import equity, run_cycle

STATE_DIR = Path(__file__).resolve().parent / "state"
STATE = STATE_DIR / "paper.json"
LIVE_STATE = STATE_DIR / "live.json"
LIVE_PORTS = {4001, 7496}  # θύρες πραγματικού λογαριασμού στο Gateway και στο TWS


def cmd_backtest(prices, _args):
    traded = prices[TRADED]
    res = run_backtest(traded, SETTINGS).loc["2010":]
    print(f"Περίοδος: {res.index[0].date()} έως {res.index[-1].date()}  |  "
          f"κόστος {SETTINGS.cost_bps:.0f} bps ανά συναλλαγή  |  {', '.join(TRADED)}\n")
    labels = {"CAGR": "Ετήσια απόδ.", "Volatility": "Μεταβλητότ.", "Sharpe": "Sharpe",
              "MaxDrawdown": "Μέγ. πτώση"}
    cols = {"Στρατηγική": res["strategy"], "Buy & hold": res["buy_hold"],
            "Μόνο χρυσός": prices["PHAU.MI"].pct_change(fill_method=None).fillna(0.0).loc["2010":]}
    for a, b in (("2010", "2017"), ("2018", "2026"), ("2010", "2026")):
        print(f"{a}-{b}".ljust(14) + "".join(f"{c:>13}" for c in cols))
        ms = [metrics(d.loc[a:b]) for d in cols.values()]
        for k, lab in labels.items():
            fmt = "{:>13.2f}" if k == "Sharpe" else "{:>13.1%}"
            print(f"{lab:14}" + "".join(fmt.format(m[k]) for m in ms))
        print()
    print(f"Μέση έκθεση στην αγορά: {res['exposure'].mean():.0%}")


def cmd_signals(prices, _args):
    w = latest_weights(prices[TRADED], SETTINGS)
    last = prices.ffill().iloc[-1]
    sma = prices.rolling(SETTINGS.trend_window).mean().iloc[-1]
    print(f"Με βάση το κλείσιμο {prices.index[-1].date()}:\n")
    print(f"  {'Σύμβολο':9}{'Εμπόρευμα':22}{'Τιμή':>9}{'vs ΜΟ200':>10}  {'Τάση':8}{'Θέση':>7}")
    for sym, name in UNIVERSE.items():
        gap = last[sym] / sma[sym] - 1
        pos = f"{w[sym]:6.1%}" if sym in w.index and w[sym] > 0 else ("     -" if sym in TRADED else "")
        print(f"  {sym:9}{name:22}{last[sym]:>9.2f}{gap:>+10.1%}  {'άνοδος' if gap > 0 else 'πτώση':8}{pos:>7}")
    print(f"\n  Επενδυμένο: {w.sum():.1%}   Μετρητά: {1 - w.sum():.1%}   "
          f"(θέσεις παίρνουμε μόνο σε: {', '.join(TRADED)})")


def cmd_paper(prices, _args):
    broker = PaperBroker(STATE, cost_bps=SETTINGS.cost_bps)
    trades = run_cycle(broker, prices[TRADED], SETTINGS)
    eq = equity(broker, prices.ffill().iloc[-1])
    broker.state["equity_log"].append({"date": str(date.today()), "equity": round(eq, 2)})
    broker.save()
    if broker.state["halted"]:
        print("KILL SWITCH ενεργό: όλες οι θέσεις έκλεισαν, δεν γίνονται νέες συναλλαγές.")
    for sym, n, px in trades:
        print(f"  {'ΑΓΟΡΑ ' if n > 0 else 'ΠΩΛΗΣΗ'} {abs(n):>5} {sym:8} @ {px:.2f}")
    if not trades:
        print("  Καμία συναλλαγή σήμερα.")
    print(f"\nΑξία χαρτοφυλακίου: {eq:,.2f}   Μετρητά: {broker.cash():,.2f}")


def cmd_status(prices, _args):
    broker = PaperBroker(STATE, cost_bps=SETTINGS.cost_bps)
    last = prices.ffill().iloc[-1]
    eq = equity(broker, last)
    print(f"Αξία: {eq:,.2f}   Υψηλό: {broker.state['peak_equity']:,.2f}   "
          f"Μετρητά: {broker.cash():,.2f}   Συναλλαγές: {len(broker.state['trades'])}"
          f"{'   [HALTED]' if broker.state['halted'] else ''}")
    for sym, n in broker.positions().items():
        print(f"  {sym:8} {n:>5} τεμ.  {n * last[sym]:>10,.2f}  ({n * last[sym] / eq:.1%})")


def cmd_reset_halt(_prices, _args):
    broker = PaperBroker(STATE, cost_bps=SETTINGS.cost_bps)
    broker.state["halted"] = False
    broker.state["peak_equity"] = broker.cash()
    broker.save()
    print("Το kill switch απενεργοποιήθηκε.")


def cmd_live(prices, args):
    from cbot.ibkr import IBKRBroker

    send = "--send" in args
    port = int(os.environ.get("IBKR_PORT", "4002"))
    if send and port in LIVE_PORTS:
        answer = input(f"Η θύρα {port} είναι ΠΡΑΓΜΑΤΙΚΟΣ λογαριασμός. Γράψε ΠΡΑΓΜΑΤΙΚΑ ΧΡΗΜΑΤΑ για να συνεχίσω: ")
        if answer.strip() != "ΠΡΑΓΜΑΤΙΚΑ ΧΡΗΜΑΤΑ":
            sys.exit("Ακυρώθηκε.")
    broker = IBKRBroker(TRADED, host=os.environ.get("IBKR_HOST", "127.0.0.1"), port=port,
                        client_id=int(os.environ.get("IBKR_CLIENT_ID", "17")),
                        max_order_value=SETTINGS.max_order_value, dry_run=not send)
    try:
        last = prices.ffill().iloc[-1]
        eq = equity(broker, last)
        state = json.loads(LIVE_STATE.read_text()) if LIVE_STATE.exists() else {"peak_equity": eq, "halted": False}
        print(f"Λογαριασμός {broker.account}, θύρα {port}, κεφάλαιο {eq:,.2f} EUR"
              f"{'' if send else '  (δοκιμή: δεν στέλνεται τίποτα)'}")
        trades = run_cycle(broker, prices[TRADED], SETTINGS, state)
        if send:
            STATE_DIR.mkdir(exist_ok=True)
            LIVE_STATE.write_text(json.dumps(state, indent=2))
        if state["halted"]:
            print("KILL SWITCH ενεργό. Για επανεκκίνηση σβήσε το state/live.json.")
        if not trades:
            print("  Καμία συναλλαγή σήμερα.")
    finally:
        broker.close()


COMMANDS = {"backtest": cmd_backtest, "signals": cmd_signals, "paper": cmd_paper,
            "status": cmd_status, "reset-halt": cmd_reset_halt, "live": cmd_live}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](load_prices(list(UNIVERSE)), sys.argv[2:])
