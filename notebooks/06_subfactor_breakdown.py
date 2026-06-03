"""Evaluate every team-coin SUB-factor separately, for both universes.
Goal: see which dimension x flip actually carries signal in US large vs small
caps, instead of looking only at the 1:1:1 composite.

Turnover proxy = pct-change of volume (activity/disagreement change), clean and
market-cap-free, identical definition across universes."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import load_prices, to_panel, RAW
from teamcoin.data_r2000 import load_r2000_prices
from teamcoin.neutralize import load_fundamentals, neutralize_cross_section

LOOKBACK = 20


def build(universe):
    if universe == "sp500":
        df = load_prices()
        sectors = load_fundamentals()["sector"]
    else:
        df = load_r2000_prices()
        sectors = pd.read_parquet(RAW / "r2000_sectors.parquet")["sector"]
    adj = to_panel(df, "adj_close").replace([np.inf, -np.inf], np.nan)
    op = to_panel(df, "open").replace([np.inf, -np.inf], np.nan)
    cl = to_panel(df, "close").replace([np.inf, -np.inf], np.nan)
    vol = to_panel(df, "volume").replace([np.inf, -np.inf], np.nan)
    ret_d = adj.pct_change()
    ret_i = (cl / op) - 1
    ret_o = (op / cl.shift(1)) - 1
    # clean turnover proxy: relative change in volume
    dturn = vol.pct_change().replace([np.inf, -np.inf], np.nan)
    return adj, ret_d, ret_i, ret_o, dturn, sectors


def flip(ret, dturn, t0, mode, distance=False):
    w = ret.loc[:t0].tail(LOOKBACK)
    if distance:
        base = (w.sub(w.mean(axis=1), axis=0)).abs().mean()
        vol20 = (w.sub(w.mean(axis=1), axis=0)).abs().std()
    else:
        base = w.mean()
        vol20 = w.std()
    if mode == "none":
        return base
    if mode == "vol":
        is_coin = vol20 < vol20.mean()
    else:  # turnover
        dt = dturn.loc[:t0].tail(LOOKBACK).mean()
        is_coin = dt < dt.mean()
    return base.where(~is_coin, -base)


def eval_factor(factor_func, adj, sectors, label):
    month_ends = adj.pct_change().resample("ME").last().index
    ics = []
    for i in range(len(month_ends) - 1):
        t0, t1 = month_ends[i], month_ends[i + 1]
        f = factor_func(t0)
        if f is None or f.dropna().empty:
            continue
        mc = adj.loc[:t0].iloc[-1]
        f = neutralize_cross_section(f.dropna(), mc, sectors)
        fwd = adj.loc[:t1].iloc[-1] / adj.loc[:t0].iloc[-1] - 1
        pair = pd.concat([f, fwd], axis=1, keys=["f", "r"]).dropna()
        if len(pair) < 100:
            continue
        ic, _ = spearmanr(pair["f"], pair["r"])
        if not np.isnan(ic):
            ics.append(ic)
    ics = np.array(ics)
    icir = ics.mean() / ics.std() if ics.std() > 0 else np.nan
    print(f"  {label:30s} IC {ics.mean():+.4f}  ICIR {icir:+.3f}  %neg {(ics<0).mean():.0%}")
    return ics.mean(), icir


def run(universe):
    adj, rd, ri, ro, dturn, sectors = build(universe)
    print(f"\n=== {universe.upper()} ({adj.shape[1]} tickers) — sub-factor breakdown ===")
    dims = [("daily", rd, False), ("intraday", ri, False), ("overnight", ro, True)]
    for dname, ret, dist in dims:
        eval_factor(lambda t0, r=ret, d=dist: flip(r, dturn, t0, "none", d),
                    adj, sectors, f"{dname}: traditional")
        eval_factor(lambda t0, r=ret, d=dist: flip(r, dturn, t0, "vol", d),
                    adj, sectors, f"{dname}: vol-flip")
        eval_factor(lambda t0, r=ret, d=dist: flip(r, dturn, t0, "turnover", d),
                    adj, sectors, f"{dname}: turnover-flip")


if __name__ == "__main__":
    run("sp500")
    run("r2000")