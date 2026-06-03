"""Transaction-cost robustness for the strongest OOS factor: traditional
overnight reversal on R2000 small caps.

Overnight reversal in small caps is suspected to be partly bid-ask bounce, not
alpha. Build the decile long-short return, then subtract realistic round-trip
costs (small-cap spreads are wide). See how much survives."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import to_panel, RAW
from teamcoin.data_r2000 import load_r2000_prices
from teamcoin.neutralize import neutralize_cross_section

LOOKBACK = 20
N_DEC = 10

df = load_r2000_prices()
adj = to_panel(df, "adj_close").replace([np.inf, -np.inf], np.nan)
op = to_panel(df, "open").replace([np.inf, -np.inf], np.nan)
cl = to_panel(df, "close").replace([np.inf, -np.inf], np.nan)
sectors = pd.read_parquet(RAW / "r2000_sectors.parquet")["sector"]
ret_o = (op / cl.shift(1)) - 1

month_ends = adj.pct_change().resample("ME").last().index

# build monthly long-short with turnover tracking
prev_long, prev_short = set(), set()
gross_rets, turnovers, dates = [], [], []

for i in range(len(month_ends) - 1):
    t0, t1 = month_ends[i], month_ends[i + 1]
    # traditional overnight reversal factor at t0
    f = ret_o.loc[:t0].tail(LOOKBACK).mean().dropna()
    if f.empty:
        continue
    mc = adj.loc[:t0].iloc[-1]
    f = neutralize_cross_section(f, mc, sectors)
    fwd = adj.loc[:t1].iloc[-1] / adj.loc[:t0].iloc[-1] - 1
    pair = pd.concat([f, fwd], axis=1, keys=["f", "r"]).dropna()
    if len(pair) < 100:
        continue
    pair["dec"] = pd.qcut(pair["f"], N_DEC, labels=False, duplicates="drop")
    # reversal: low factor (most negative past overnight) -> long
    longs = set(pair.index[pair["dec"] == 0])
    shorts = set(pair.index[pair["dec"] == N_DEC - 1])
    gross = pair.loc[pair["dec"] == 0, "r"].mean() - pair.loc[pair["dec"] == N_DEC - 1, "r"].mean()
    # turnover = fraction of names changed vs last month (both legs)
    if prev_long or prev_short:
        chg = (len(longs ^ prev_long) + len(shorts ^ prev_short))
        tot = (len(longs) + len(shorts))
        turn = chg / tot if tot else 1.0
    else:
        turn = 1.0
    gross_rets.append(gross)
    turnovers.append(turn)
    dates.append(t1)
    prev_long, prev_short = longs, shorts

gross = pd.Series(gross_rets, index=pd.DatetimeIndex(dates))
turn = pd.Series(turnovers, index=pd.DatetimeIndex(dates))
print(f"months: {len(gross)}, avg monthly turnover: {turn.mean():.1%}")
print(f"\ntraditional overnight reversal long-short, R2000:")
print(f"{'round-trip cost':>18s} {'ann return':>12s} {'IR':>8s} {'final NAV':>10s}")

for cost in [0.0, 0.001, 0.002, 0.003, 0.005]:
    net = gross - turn * cost * 2   # cost per side, both legs traded at `turn`
    ann = net.mean() * 12
    ir = ann / (net.std() * np.sqrt(12)) if net.std() > 0 else np.nan
    nav = (1 + net).cumprod().iloc[-1]
    print(f"{cost*100:>16.1f}% {ann:>+11.2%} {ir:>+8.2f} {nav:>10.3f}")

print("\n(small-cap one-way spreads are often 0.2-0.5%+, so realistic round-trip")
print(" cost is in the 0.2-0.5% range applied to turnover.)")