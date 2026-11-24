"""Σύνδεση με Interactive Brokers μέσω TWS ή IB Gateway (βιβλιοθήκη ib_async).

ΔΕΝ έχει δοκιμαστεί απέναντι σε πραγματικό λογαριασμό. Πρώτη χρήση πάντα σε paper
λογαριασμό της IBKR (θύρα 4002 στο Gateway, 7497 στο TWS).

Ο λογαριασμός πρέπει να είναι αποκλειστικά για το bot: θεωρεί δικό του κεφάλαιο όλα
τα μετρητά σε ευρώ και όσες θέσεις έχει στα σύμβολα που διαπραγματεύεται.
"""
from .broker import Broker

EXCHANGE = "BVME.ETF"   # Borsa Italiana ETFplus, όπως το ονομάζει η IBKR
LIMIT_BUFFER = 0.005    # οριακή εντολή έως 0,5% χειρότερα από την τελευταία τιμή
FILL_TIMEOUT = 60       # δευτερόλεπτα αναμονής πριν ακυρωθεί η εντολή


class IBKRBroker(Broker):
    def __init__(self, symbols, host="127.0.0.1", port=4002, client_id=17,
                 max_order_value=2000.0, dry_run=True):
        from ib_async import IB, Stock  # εισάγεται εδώ για να μη χρειάζεται στο paper/backtest

        self.dry_run = dry_run
        self.max_order_value = max_order_value
        self.ib = IB()
        self.ib.connect(host, port, clientId=client_id, readonly=dry_run)
        self.account = self.ib.managedAccounts()[0]
        self.contracts = {}
        for sym in symbols:
            c = Stock(sym.split(".")[0], EXCHANGE, "EUR")
            if not self.ib.qualifyContracts(c) or not c.conId:
                raise RuntimeError(f"Η IBKR δεν βρήκε το {sym} στο {EXCHANGE}. Δεν στέλνω καμία εντολή.")
            self.contracts[sym] = c
        self._by_conid = {c.conId: sym for sym, c in self.contracts.items()}

    def close(self):
        self.ib.disconnect()

    def cash(self) -> float:
        for v in self.ib.accountValues(self.account):
            if v.tag == "TotalCashBalance" and v.currency == "EUR":
                return float(v.value)
        raise RuntimeError("Δεν βρέθηκε υπόλοιπο μετρητών σε ευρώ στον λογαριασμό.")

    def positions(self) -> dict:
        out = {}
        for p in self.ib.positions(self.account):
            sym = self._by_conid.get(p.contract.conId)
            if sym and p.position:
                out[sym] = int(p.position)
        return out

    def order(self, symbol: str, shares: int, price: float) -> None:
        from ib_async import LimitOrder

        if shares == 0:
            return
        if shares < 0 and -shares > self.positions().get(symbol, 0):
            raise ValueError(f"Δεν επιτρέπεται short στο {symbol}")
        if abs(shares) * price > self.max_order_value:
            raise ValueError(f"Εντολή {symbol} αξίας {abs(shares) * price:.0f} EUR ξεπερνά το όριο "
                             f"{self.max_order_value:.0f} EUR")
        side = "BUY" if shares > 0 else "SELL"
        limit = round(price * (1 + LIMIT_BUFFER if shares > 0 else 1 - LIMIT_BUFFER), 2)
        if self.dry_run:
            print(f"  [δοκιμή, δεν στάλθηκε] {side} {abs(shares)} {symbol} όριο {limit}")
            return
        trade = self.ib.placeOrder(self.contracts[symbol], LimitOrder(side, abs(shares), limit, tif="DAY"))
        waited = 0
        while not trade.isDone() and waited < FILL_TIMEOUT:
            self.ib.sleep(1)
            waited += 1
        if not trade.isDone():
            self.ib.cancelOrder(trade.order)
            self.ib.sleep(2)
        print(f"  {side} {abs(shares)} {symbol} όριο {limit}: {trade.orderStatus.status}, "
              f"εκτελέστηκαν {trade.orderStatus.filled:.0f}")
