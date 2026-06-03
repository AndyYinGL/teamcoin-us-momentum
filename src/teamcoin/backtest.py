"""Decile long-short backtest for a factor (monthly rebalance).

Factor here is NEGATIVE (reversal-like): low factor value -> high future return.
So we go LONG the lowest-decile and SHORT the highest-decile.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import load_prices, to_panel
from teamcoin.neutralize import load_fundamentals, neutralize_cross_section
from teamcoin.factors import build_panels, make_factor_funcs

N_DECILES = 10


def backtest_factor(factor_func, adj, fund, neutralize=True):
    """Return (decile_ann_returns, ls_monthly_returns, ls_nav)."""
    ret = adj.pct_change()
    month_ends = ret.resample("ME").last().index
    decile_rets = {d: [] for d in range(N_DECILES)}
    ls_rets = []
    dates = []
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
        if len(pair) < N_DECILES * 5:
            continue
        pair["decile"] = pd.qcut(pair["f"], N_DECILES, labels=False, duplicates="drop")
        grp = pair.groupby("decile")["r"].mean()
        for d in range(N_DECILES):
            if d in grp.index:
                decile_rets[d].append(grp[d])
        # long lowest decile (0), short highest (9)
        if 0 in grp.index and (N_DECILES - 1) in grp.index:
            ls_rets.append(grp[0] - grp[N_DECILES - 1])
            dates.append(t1)
    # annualized return per decile (monthly mean * 12)
    decile_ann = {d: np.mean(v) * 12 for d, v in decile_rets.items() if v}
    ls = pd.Series(ls_rets, index=pd.DatetimeIndex(dates))
    nav = (1 + ls).cumprod()
    return decile_ann, ls, nav


def summarize(ls, label):
    ann = ls.mean() * 12
    vol = ls.std() * np.sqrt(12)
    ir = ann / vol if vol > 0 else np.nan
    win = (ls > 0).mean()
    nav = (1 + ls).cumprod()
    mdd = (nav / nav.cummax() - 1).min()
    print(f"{label}")
    print(f"  long-short annualized return: {ann:+.2%}")
    print(f"  annualized vol:               {vol:.2%}")
    print(f"  information ratio:            {ir:+.2f}")
    print(f"  monthly win rate:             {win:.1%}")
    print(f"  max drawdown:                 {mdd:.2%}")
    print(f"  final NAV (from 1.0):         {nav.iloc[-1]:.3f}")


if __name__ == "__main__":
    adj, rd, ri, ro, turnover, fund = build_panels()
    f = make_factor_funcs(rd, ri, ro, turnover)

    print("=== Team-coin factor: decile long-short backtest (US S&P500) ===")
    print("A-share ref: team-coin long-short annualized +39.69%, IR 3.95\n")
    decile_ann, ls, nav = backtest_factor(f["team_coin"], adj, fund)
    print("decile annualized returns (decile 0 = lowest factor = should be highest):")
    for d in sorted(decile_ann):
        print(f"  decile {d}: {decile_ann[d]:+.2%}")
    print()
    summarize(ls, "TEAM-COIN long-short (long D0, short D9)")