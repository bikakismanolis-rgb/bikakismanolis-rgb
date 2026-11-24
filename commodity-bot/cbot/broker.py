"""Brokers. Το PaperBroker εκτελεί εικονικές εντολές. Ο πραγματικός broker
(Interactive Brokers) είναι στο ibkr.py και υλοποιεί την ίδια διεπαφή."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
from pathlib import Path


class Broker(ABC):
    @abstractmethod
    def cash(self) -> float: ...

    @abstractmethod
    def positions(self) -> dict: ...

    @abstractmethod
    def order(self, symbol: str, shares: int, price: float) -> None:
        """shares > 0 αγορά, shares < 0 πώληση."""


class PaperBroker(Broker):
    def __init__(self, path: Path, start_cash: float = 10_000.0, cost_bps: float = 10.0):
        self.path = Path(path)
        self.cost_bps = cost_bps
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            self.state = {"cash": start_cash, "positions": {}, "peak_equity": start_cash,
                          "halted": False, "trades": [], "equity_log": []}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))

    def cash(self) -> float:
        return self.state["cash"]

    def positions(self) -> dict:
        return dict(self.state["positions"])

    def order(self, symbol: str, shares: int, price: float) -> None:
        if shares == 0:
            return
        held = self.state["positions"].get(symbol, 0)
        if shares < 0 and -shares > held:
            raise ValueError(f"Δεν επιτρέπεται short: {symbol} έχει {held}, ζητήθηκε πώληση {-shares}")
        fee = abs(shares) * price * self.cost_bps / 1e4
        cost = shares * price + fee
        if cost > self.state["cash"] + 1e-9:
            raise ValueError(f"Ανεπαρκή μετρητά για {symbol}: χρειάζονται {cost:.2f}")
        self.state["cash"] -= cost
        new = held + shares
        if new:
            self.state["positions"][symbol] = new
        else:
            self.state["positions"].pop(symbol, None)
        self.state["trades"].append({
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "symbol": symbol, "shares": shares, "price": round(price, 4), "fee": round(fee, 4),
        })
