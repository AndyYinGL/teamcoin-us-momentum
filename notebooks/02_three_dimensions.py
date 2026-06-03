"""Check the SIGN of the traditional reversal factor across all three return
dimensions (intraday-close, intraday, overnight), mirroring the A-share report.
A-shares: daily -6.5%, intraday -6.9%, overnight +2.4%."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import load_prices, to_panel

df = load_prices()
adj = to_panel(df, "adj_close")
op = to_panel(df, "open")
cl = to_panel(df, "close")

# three daily return definitions (report's framing)
ret_daily = adj.pct_change()                       # close-to-close (adjusted)
ret_intraday = (cl / op) - 1                        # open -> close, same day
ret_overnight = (op / cl.shift(1)) - 1              # prev close -> open

def reversal_ic(ret, label):
    month_ends = ret.resample("ME").last().index
    ics = []
    for i in range(len(month_ends) - 1):
        t0, t1 = month_ends[i], month_ends[i + 1]
        factor = ret.loc[:t0].tail(20).mean()
        fwd = adj.loc[:t1].iloc[-1] / adj.loc[:t0].iloc[-1] - 1
        pair = pd.concat([factor, fwd], axis=1, keys=["f", "r"]).dropna()
        if len(pair) < 50:
            continue
        ic, _ = spearmanr(pair["f"], pair["r"])
        ics.append(ic)
    ics = np.array(ics)
    sign = "NEG (reversal)" if ics.mean() < 0 else "POS (momentum)"
    print(f"{label:22s} mean IC {ics.mean():+.4f}  ICIR {ics.mean()/ics.std():+.3f}  "
          f"%neg {(ics<0).mean():.0%}  -> {sign}")
    return ics

print("=== Traditional reversal factor, 3 return dimensions (US S&P500) ===")
print(f"{'dimension':22s} {'A-share ref':>12s}")
print(f"{'daily (close-close)':22s} {'-6.53%':>12s}")
reversal_ic(ret_daily, "  US daily")
print(f"{'intraday (open-close)':22s} {'-6.93%':>12s}")
reversal_ic(ret_intraday, "  US intraday")
print(f"{'overnight (prevC-open)':22s} {'+2.36%':>12s}")
reversal_ic(ret_overnight, "  US overnight")