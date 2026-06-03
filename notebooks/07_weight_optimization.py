"""Weight optimization for the team-coin sub-factors, walk-forward OOS.

Compares four ways to combine sub-factors, all out-of-sample:
  1. naive baseline   - traditional overnight reversal alone (strongest single)
  2. equal weight     - report's 1:1:1 of corrected dimensions
  3. rolling IR weight - weight each sub-factor by trailing 24m ICIR
  4. Ridge ML         - learn linear weights on trailing 24m, predict next month

Key discipline: weights are learned ONLY on past data; IC is always next-month
OOS. Goal: can any learned combination beat the naive reversal baseline?
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path.home() / "teamcoin-us-momentum" / "src"))
from teamcoin.data import to_panel, RAW
from teamcoin.data_r2000 import load_r2000_prices
from teamcoin.neutralize import neutralize_cross_section

LOOKBACK = 20
TRAIN_M = 24   # trailing months to learn weights

df = load_r2000_prices()
adj = to_panel(df, "adj_close").replace([np.inf, -np.inf], np.nan)
op = to_panel(df, "open").replace([np.inf, -np.inf], np.nan)
cl = to_panel(df, "close").replace([np.inf, -np.inf], np.nan)
vol = to_panel(df, "volume").replace([np.inf, -np.inf], np.nan)
sectors = pd.read_parquet(RAW / "r2000_sectors.parquet")["sector"]
ret_d = adj.pct_change()
ret_i = (cl / op) - 1
ret_o = (op / cl.shift(1)) - 1
dturn = vol.pct_change().replace([np.inf, -np.inf], np.nan)


def flip(ret, t0, mode, distance=False):
    w = ret.loc[:t0].tail(LOOKBACK)
    if distance:
        base = (w.sub(w.mean(axis=1), axis=0)).abs().mean()
    else:
        base = w.mean()
    if mode == "none":
        return base
    if mode == "vol":
        v = (w.sub(w.mean(axis=1), axis=0)).abs().std() if distance else w.std()
        coin = v < v.mean()
    else:
        dt = dturn.loc[:t0].tail(LOOKBACK).mean()
        coin = dt < dt.mean()
    return base.where(~coin, -base)


# sub-factor library (name -> func(t0)->series)
SUBS = {
    "trad_daily": lambda t0: flip(ret_d, t0, "none"),
    "trad_intra": lambda t0: flip(ret_i, t0, "none"),
    "trad_overnight": lambda t0: flip(ret_o, t0, "none", True),
    "turn_daily": lambda t0: flip(ret_d, t0, "turnover"),
    "turn_intra": lambda t0: flip(ret_i, t0, "turnover"),
    "turn_overnight": lambda t0: flip(ret_o, t0, "turnover", True),
}
NAMES = list(SUBS)

month_ends = ret_d.resample("ME").last().index


def zscore(s):
    return (s - s.mean()) / s.std()


# Precompute, per month: neutralized sub-factor matrix + forward return
print("precomputing sub-factors per month...")
panel = {}  # t0 -> (DataFrame[tickers x subs], fwd Series)
for i in range(len(month_ends) - 1):
    t0, t1 = month_ends[i], month_ends[i + 1]
    cols = {}
    for nm in NAMES:
        f = SUBS[nm](t0).dropna()
        if f.empty:
            continue
        mc = adj.loc[:t0].iloc[-1]
        cols[nm] = neutralize_cross_section(f, mc, sectors)
    if len(cols) < len(NAMES):
        continue
    mat = pd.DataFrame(cols).dropna()
    mat = mat.apply(zscore)
    fwd = adj.loc[:t1].iloc[-1] / adj.loc[:t0].iloc[-1] - 1
    common = mat.index.intersection(fwd.dropna().index)
    if len(common) < 100:
        continue
    panel[t0] = (mat.loc[common], fwd.loc[common])

keys = sorted(panel)
print(f"usable months: {len(keys)}")


def ic_of(weight_func):
    """weight_func(history_keys) -> weight Series over NAMES (or None to skip)."""
    ics = []
    for j in range(TRAIN_M, len(keys)):
        t0 = keys[j]
        mat, fwd = panel[t0]
        w = weight_func(keys[:j])
        if w is None:
            continue
        score = (mat[NAMES] * w[NAMES]).sum(axis=1)
        ic, _ = spearmanr(score, fwd)
        if not np.isnan(ic):
            ics.append(ic)
    ics = np.array(ics)
    return ics.mean(), (ics.mean() / ics.std() if ics.std() > 0 else np.nan), ics


# 1. naive: traditional overnight only
def w_naive(hist):
    w = pd.Series(0.0, index=NAMES); w["trad_overnight"] = 1.0; return w

# 2. equal weight of the 3 traditional (report-style reversal composite)
def w_equal(hist):
    w = pd.Series(0.0, index=NAMES)
    for nm in ["trad_daily", "trad_intra", "trad_overnight"]:
        w[nm] = 1 / 3
    return w

# 3. rolling IR weight over all 6 subs
def w_ir(hist):
    win = hist[-TRAIN_M:]
    irs = {}
    for nm in NAMES:
        s = []
        for t0 in win:
            mat, fwd = panel[t0]
            ic, _ = spearmanr(mat[nm], fwd)
            if not np.isnan(ic):
                s.append(ic)
        s = np.array(s)
        irs[nm] = s.mean() / s.std() if len(s) > 2 and s.std() > 0 else 0.0
    w = pd.Series(irs)
    return w / w.abs().sum() if w.abs().sum() > 0 else w

# 4. Ridge ML: learn weights mapping subs -> fwd on pooled trailing window
def w_ridge(hist):
    win = hist[-TRAIN_M:]
    X, y = [], []
    for t0 in win:
        mat, fwd = panel[t0]
        X.append(mat[NAMES].values)
        y.append(fwd.values)
    X = np.vstack(X); y = np.concatenate(y)
    m = Ridge(alpha=10.0).fit(X, y)
    return pd.Series(m.coef_, index=NAMES)


print("\n=== Walk-forward OOS IC (R2000 small caps), trailing 24m to learn ===")
for label, wf in [("1. naive (trad overnight only)", w_naive),
                  ("2. equal-weight 3 traditional", w_equal),
                  ("3. rolling IR weight (6 subs)", w_ir),
                  ("4. Ridge ML (6 subs)", w_ridge)]:
    ic, icir, _ = ic_of(wf)
    print(f"  {label:34s} OOS IC {ic:+.4f}  ICIR {icir:+.3f}")