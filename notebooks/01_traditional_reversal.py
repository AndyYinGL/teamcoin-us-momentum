"""First empirical check: what is the SIGN of the traditional reversal factor
in U.S. large caps? In A-shares it's negative (reversal). U.S. equities are
momentum-driven, so we expect it to be weaker or even positive."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import load_prices, to_panel

df = load_prices()
close = to_panel(df, "adj_close")
print(f"panel: {close.shape[0]} days x {close.shape[1]} tickers")

# daily simple returns
ret = close.pct_change()

# month-end rebalance dates
month_ends = ret.resample("ME").last().index

ics = []
for i in range(len(month_ends) - 1):
    t0, t1 = month_ends[i], month_ends[i + 1]
    # factor: mean of last 20 daily returns up to t0
    window = ret.loc[:t0].tail(20)
    factor = window.mean()
    # forward return: t0 -> t1 (next month)
    fwd = close.loc[:t1].iloc[-1] / close.loc[:t0].iloc[-1] - 1
    # align, drop NaN
    pair = pd.concat([factor, fwd], axis=1, keys=["factor", "fwd"]).dropna()
    if len(pair) < 50:
        continue
    ic, _ = spearmanr(pair["factor"], pair["fwd"])
    ics.append(ic)

ics = np.array(ics)
print(f"\n=== Traditional reversal factor (past-20d mean return) ===")
print(f"months tested: {len(ics)}")
print(f"mean Rank IC: {ics.mean():.4f}")
print(f"IC std: {ics.std():.4f}")
print(f"ICIR: {ics.mean() / ics.std():.3f}")
print(f"% months IC < 0: {(ics < 0).mean():.1%}")
print(f"\nInterpretation: A-shares ~ -6.5% (reversal). "
      f"US sign here = {'NEGATIVE (reversal)' if ics.mean() < 0 else 'POSITIVE (momentum)'}")