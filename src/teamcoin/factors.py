"""Team-coin factor construction (full three dimensions).

Mechanism (Founder Securities report):
  - reversal factor per dimension = mean of last 20 daily returns
  - 'knowability' split: low-vol / low-turnover-change stocks are 'coins'
    (high knowability -> future momentum) -> FLIP reversal value (x -1);
    high-vol / high-turnover-change stocks are 'teams' -> keep.
  - overnight uses 'distance from market mean' (|overnight - cross-sec mean|).
  - per dimension: vol-flip + turnover-flip, equal weight -> corrected reversal.
  - three corrected reversals, equal weight -> team-coin factor.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import load_prices, to_panel
from teamcoin.neutralize import load_fundamentals, neutralize_cross_section

LOOKBACK = 20


def build_panels():
    df = load_prices()
    adj = to_panel(df, "adj_close")
    op = to_panel(df, "open")
    cl = to_panel(df, "close")
    vol = to_panel(df, "volume")
    fund = load_fundamentals()
    shares = fund["shares_out"]
    turnover = vol.divide(shares.reindex(vol.columns), axis=1)
    ret_daily = adj.pct_change()
    ret_intraday = (cl / op) - 1
    ret_overnight = (op / cl.shift(1)) - 1
    return adj, ret_daily, ret_intraday, ret_overnight, turnover, fund


def _zscore_cs(s):
    """Cross-sectional standardize so 3 dimensions combine on equal footing."""
    return (s - s.mean()) / s.std()


def make_factor_funcs(ret_daily, ret_intraday, ret_overnight, turnover):
    """Return a dict of factor_func(t0)->Series for every report factor."""

    def dturn(t0):
        return turnover.diff().loc[:t0].tail(LOOKBACK).mean()

    # ---- generic vol-flip / turnover-flip on a given return panel ----
    def vol_flip(ret, t0, distance=False):
        w = ret.loc[:t0].tail(LOOKBACK)
        if distance:
            # overnight: 'distance' = |daily overnight - cross-sec mean|, then mean
            dist = (w.sub(w.mean(axis=1), axis=0)).abs()
            base = dist.mean()
            vol20 = dist.std()
        else:
            base = w.mean()
            vol20 = w.std()
        is_coin = vol20 < vol20.mean()
        return base.where(~is_coin, -base)

    def turn_flip(ret, t0, distance=False):
        w = ret.loc[:t0].tail(LOOKBACK)
        if distance:
            dist = (w.sub(w.mean(axis=1), axis=0)).abs()
            base = dist.mean()
        else:
            base = w.mean()
        dt = dturn(t0)
        is_coin = dt < dt.mean()
        return base.where(~is_coin, -base)

    funcs = {}
    # daily
    funcs["trad_daily"] = lambda t0: ret_daily.loc[:t0].tail(LOOKBACK).mean()
    funcs["daily_volflip"] = lambda t0: vol_flip(ret_daily, t0)
    funcs["daily_turnflip"] = lambda t0: turn_flip(ret_daily, t0)
    funcs["daily_corrected"] = lambda t0: _zscore_cs(vol_flip(ret_daily, t0)) + _zscore_cs(turn_flip(ret_daily, t0))
    # intraday
    funcs["trad_intraday"] = lambda t0: ret_intraday.loc[:t0].tail(LOOKBACK).mean()
    funcs["intraday_volflip"] = lambda t0: vol_flip(ret_intraday, t0)
    funcs["intraday_turnflip"] = lambda t0: turn_flip(ret_intraday, t0)
    funcs["intraday_corrected"] = lambda t0: _zscore_cs(vol_flip(ret_intraday, t0)) + _zscore_cs(turn_flip(ret_intraday, t0))
    # overnight (distance-based)
    funcs["overnight_volflip"] = lambda t0: vol_flip(ret_overnight, t0, distance=True)
    funcs["overnight_turnflip"] = lambda t0: turn_flip(ret_overnight, t0, distance=True)
    funcs["overnight_corrected"] = lambda t0: _zscore_cs(vol_flip(ret_overnight, t0, distance=True)) + _zscore_cs(turn_flip(ret_overnight, t0, distance=True))
    # final team-coin: equal weight of 3 corrected
    funcs["team_coin"] = lambda t0: (
        _zscore_cs(funcs["daily_corrected"](t0))
        + _zscore_cs(funcs["intraday_corrected"](t0))
        + _zscore_cs(funcs["overnight_corrected"](t0))
    )
    return funcs


def rank_ic_series(factor_func, adj, fund, label, neutralize=False):
    ret = adj.pct_change()
    month_ends = ret.resample("ME").last().index
    ics, nmp = [], []
    for i in range(len(month_ends) - 1):
        t0, t1 = month_ends[i], month_ends[i + 1]
        factor = factor_func(t0)
        if factor is None or factor.dropna().empty:
            continue
        if neutralize:
            mc = adj.loc[:t0].iloc[-1] * fund["shares_out"].reindex(adj.columns)
            factor = neutralize_cross_section(factor.dropna(), mc, fund["sector"])
        fwd = adj.loc[:t1].iloc[-1] / adj.loc[:t0].iloc[-1] - 1
        pair = pd.concat([factor, fwd], axis=1, keys=["f", "r"]).dropna()
        if len(pair) < 50:
            continue
        ic, _ = spearmanr(pair["f"], pair["r"])
        ics.append(ic)
        ex_f = pair["f"] - pair["f"].mean()
        ex_r = pair["r"] - pair["r"].mean()
        agree = np.sign(ex_f) == np.sign(ex_r)
        nmp.append((agree.sum() - (~agree).sum()) / len(agree))
    ics, nmp = np.array(ics), np.array(nmp)
    print(f"{label:26s} IC {ics.mean():+.4f}  ICIR {ics.mean()/ics.std():+.3f}  "
          f"%neg {(ics<0).mean():.0%}  netMom {nmp.mean():+.4f}")
    return ics


if __name__ == "__main__":
    adj, rd, ri, ro, turnover, fund = build_panels()
    f = make_factor_funcs(rd, ri, ro, turnover)

    print("=== Full team-coin replication on US S&P500 (neutralized) ===")
    print("A-share refs: trad_daily -6.5%, daily_corrected -8.8%, team_coin -9.7%\n")
    order = ["trad_daily", "daily_volflip", "daily_turnflip", "daily_corrected",
             "trad_intraday", "intraday_volflip", "intraday_turnflip", "intraday_corrected",
             "overnight_volflip", "overnight_turnflip", "overnight_corrected",
             "team_coin"]
    for name in order:
        rank_ic_series(f[name], adj, fund, name, neutralize=True)