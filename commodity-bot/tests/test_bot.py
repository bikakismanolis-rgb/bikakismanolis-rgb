import numpy as np
import pandas as pd
import pytest

from cbot.backtest import run_backtest
from cbot.broker import PaperBroker
from cbot.config import Settings
from cbot.strategy import target_weights
from cbot.trader import equity, run_cycle

S = Settings(trend_window=20, vol_window=10)


def make_prices(n=300, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    up = 100 * np.cumprod(1 + 0.004 + 0.005 * rng.standard_normal(n))
    down = 100 * np.cumprod(1 - 0.004 + 0.005 * rng.standard_normal(n))
    return pd.DataFrame({"UP": up, "DOWN": down}, index=idx)


def test_weights_respect_limits():
    w = target_weights(make_prices(), S)
    assert (w >= 0).all().all()
    assert (w <= S.max_weight + 1e-12).all().all()
    assert (w.sum(axis=1) <= S.max_gross + 1e-12).all()
    assert w["UP"].mean() > w["DOWN"].mean()


def test_no_lookahead():
    p = make_prices()
    full = target_weights(p, S)
    cut = target_weights(p.iloc[:200], S)
    pd.testing.assert_frame_equal(full.iloc[:200], cut)


def test_backtest_ignores_future_prices():
    p = make_prices()
    a = run_backtest(p, S)["strategy"]
    q = p.copy()
    q.iloc[250:] *= 5
    b = run_backtest(q, S)["strategy"]
    pd.testing.assert_series_equal(a.iloc[:250], b.iloc[:250])


def test_paper_cycle_and_limits(tmp_path):
    p = make_prices()
    b = PaperBroker(tmp_path / "s.json", start_cash=10_000, cost_bps=10)
    trades = run_cycle(b, p, S)
    last = p.iloc[-1]
    assert trades and b.cash() >= 0
    eq = equity(b, last)
    for sym, n in b.positions().items():
        assert n > 0 and n * last[sym] / eq <= S.max_weight + 0.01
    assert run_cycle(b, p, S) == []  # δεύτερο τρέξιμο την ίδια μέρα δεν κάνει τίποτα


def test_no_short_no_overdraft(tmp_path):
    b = PaperBroker(tmp_path / "s.json", start_cash=1_000)
    with pytest.raises(ValueError):
        b.order("X", -1, 10)
    with pytest.raises(ValueError):
        b.order("X", 1000, 10)


def test_kill_switch(tmp_path):
    p = make_prices()
    b = PaperBroker(tmp_path / "s.json", start_cash=10_000)
    run_cycle(b, p, S)
    assert b.positions()
    b.state["peak_equity"] = 100_000  # προσομοίωση μεγάλης πτώσης
    run_cycle(b, p, S)
    assert b.state["halted"] and not b.positions()
    assert run_cycle(b, p, S) == []


def test_clean_prices_fixes_bad_ticks_and_rescaling():
    from cbot.data import clean_prices
    idx = pd.bdate_range("2020-01-01", periods=60)
    true = pd.Series(100 * 1.001 ** np.arange(60), index=idx)
    dirty = true.copy()
    dirty.iloc[20] *= 1.4          # μεμονωμένη λάθος τιμή
    dirty.iloc[:40] /= 50          # αλλαγή κλίμακας που δεν έχει προσαρμοστεί
    out = clean_prices(pd.DataFrame({"X": dirty}))["X"]
    assert out.iloc[-1] == pytest.approx(true.iloc[-1])
    assert out.pct_change().abs().max() < 0.01
    assert out.iloc[0] == pytest.approx(true.iloc[0], rel=0.01)


def test_run_cycle_with_external_state(tmp_path):
    p = make_prices()
    b = PaperBroker(tmp_path / "s.json", start_cash=10_000)
    state = {"peak_equity": 10_000, "halted": True}
    assert run_cycle(b, p, S, state) == [] and not b.positions()
