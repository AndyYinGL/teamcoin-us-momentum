"""Cross-sectional neutralization: regress a factor on log(market cap) and
sector dummies each period, return the residual. Mirrors the A-share report's
market-cap + industry orthogonalization."""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path.home() / "teamcoin-us-momentum"
RAW = ROOT / "data" / "raw"


def load_fundamentals():
    return pd.read_parquet(RAW / "sp500_fundamentals.parquet")


def neutralize_cross_section(factor, mktcap, sector):
    """factor, mktcap: pd.Series indexed by ticker (one date).
    sector: pd.Series ticker -> sector string.
    Returns residual factor (market-cap + sector neutralized)."""
    d = pd.concat([factor.rename("f"), mktcap.rename("mc")], axis=1).dropna()
    d = d[d["mc"] > 0]
    d["sector"] = sector.reindex(d.index)
    d = d.dropna(subset=["sector"])
    if len(d) < 30:
        return pd.Series(dtype=float)
    # design matrix: log mktcap + sector dummies (drop_first to avoid collinearity)
    X = pd.DataFrame({"log_mc": np.log(d["mc"])}, index=d.index)
    dummies = pd.get_dummies(d["sector"], drop_first=True).astype(float)
    X = pd.concat([X, dummies], axis=1)
    X.insert(0, "const", 1.0)
    y = d["f"].values
    Xv = X.values
    # OLS via lstsq
    beta, *_ = np.linalg.lstsq(Xv, y, rcond=None)
    resid = y - Xv @ beta
    return pd.Series(resid, index=d.index)


if __name__ == "__main__":
    fund = load_fundamentals()
    print("fundamentals loaded:", fund.shape)
    print("sectors:", fund["sector"].nunique())
    # quick self-test on dummy data
    import numpy as np
    rng = np.random.default_rng(0)
    tk = fund.index[:100]
    f = pd.Series(rng.normal(size=len(tk)), index=tk)
    mc = pd.Series(rng.lognormal(size=len(tk)) * 1e9, index=tk)
    out = neutralize_cross_section(f, mc, fund["sector"])
    print("neutralized output len:", len(out))
    print("mean abs resid:", out.abs().mean().round(4))