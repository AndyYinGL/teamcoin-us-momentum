"""Fetch per-ticker fundamentals (sector, shares outstanding, market cap)
from yfinance. NOTE: these are CURRENT snapshots, not historical series — a
known approximation (documented in README). Cached to parquet."""
import time
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path.home() / "teamcoin-us-momentum"
RAW = ROOT / "data" / "raw"


def fetch_fundamentals(tickers):
    """Return a DataFrame indexed by ticker with sector, shares, market_cap."""
    rows = []
    failed = []
    for n, t in enumerate(tickers, 1):
        if n % 50 == 0:
            print(f"  {n}/{len(tickers)} ...")
        try:
            info = yf.Ticker(t).info
            rows.append({
                "ticker": t,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "shares_out": info.get("sharesOutstanding"),
                "market_cap": info.get("marketCap"),
            })
        except Exception as e:
            failed.append(t)
            rows.append({"ticker": t, "sector": None, "industry": None,
                         "shares_out": None, "market_cap": None})
        time.sleep(0.3)
    df = pd.DataFrame(rows).set_index("ticker")
    print(f"\ngot {df['sector'].notna().sum()}/{len(df)} with sector")
    print(f"    {df['shares_out'].notna().sum()}/{len(df)} with shares_out")
    if failed:
        print(f"failed ({len(failed)}): {failed[:10]}{'...' if len(failed) > 10 else ''}")
    return df


if __name__ == "__main__":
    from teamcoin.universe import get_sp500_tickers
    from teamcoin.data import load_prices
    # only fetch fundamentals for tickers we actually have prices for
    have = sorted(load_prices()["ticker"].unique())
    print(f"fetching fundamentals for {len(have)} tickers (current snapshot)")
    fund = fetch_fundamentals(have)
    out = RAW / "sp500_fundamentals.parquet"
    fund.to_parquet(out)
    print(f"saved {out}")
    print("\n=== sector counts ===")
    print(fund["sector"].value_counts())