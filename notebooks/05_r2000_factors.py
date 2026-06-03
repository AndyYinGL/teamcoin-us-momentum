"""Run the full team-coin factor on Russell 2000 (IWM) small caps.
Small caps are where short-term reversal inefficiency is most likely to persist.
Sector neutralization uses IWM's GICS sectors; market-cap proxy uses log(price)
(no historical share count for this universe)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import to_panel, RAW
from teamcoin.data_r2000 import load_r2000_prices
from teamcoin.factors import make_factor_funcs
from teamcoin.neutralize import neutralize_cross_section

# load R2000 prices + sector map
df = load_r2000_prices()
adj = to_panel(df, "adj_close")
op = to_panel(df, "open")
cl = to_panel(df, "close")
vol = to_panel(df, "volume")
sectors = pd.read_parquet(RAW / "r2000_sectors.parquet")["sector"]
print(f"panel: {adj.shape[0]} days x {adj.shape[1]} tickers")

# turnover proxy: small caps have no share count here -> use dollar volume change
# as the 'disagreement' proxy (volume * price), which is the report's spirit
turnover = vol * cl   # dollar volume as turnover-like activity proxy
ret_daily = adj.pct_change()
ret_intraday = (cl / op) - 1
ret_overnight = (op / cl.shift(1)) - 1

f = make_factor_funcs(ret_daily, ret_intraday, ret_overnight, turnover)


def rank_ic(factor_func, label, neutralize=True):
    month_ends = ret_daily.resample("ME").last().index
    ics, nmp = [], []
    for i in range(len(month_ends) - 1):
        t0, t1 = month_ends[i], month_ends[i + 1]
        factor = factor_func(t0)
        if factor is None or factor.dropna().empty:
            continue
        if neutralize:
            # market-cap proxy: log(price) at t0 (no share count for R2000)
            mc = adj.loc[:t0].iloc[-1]
            factor = neutralize_cross_section(factor.dropna(), mc, sectors)
        fwd = adj.loc[:t1].iloc[-1] / adj.loc[:t0].iloc[-1] - 1
        pair = pd.concat([factor, fwd], axis=1, keys=["f", "r"]).dropna()
        if len(pair) < 100:
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


print("\n=== Team-coin on Russell 2000 small caps (neutralized) ===")
print("Refs: A-share team_coin -9.7%/-4.73 ; US large-cap team_coin -1.6%/-0.27\n")
for name in ["trad_daily", "daily_corrected", "intraday_corrected",
             "overnight_corrected", "team_coin"]:
    rank_ic(f[name], name)