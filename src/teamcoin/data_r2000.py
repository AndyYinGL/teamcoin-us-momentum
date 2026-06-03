"""Download and cache daily OHLCV for the Russell 2000 (IWM) universe.
Reuses the batch download logic; saves to a separate parquet cache.
Expect more failures than S&P 500 (small caps delist/rename more often)."""
from pathlib import Path
import pandas as pd
from teamcoin.data import download_prices, RAW
from teamcoin.universe_r2000 import get_r2000_tickers

START = "2018-01-01"
END = "2024-12-31"


def load_r2000_prices():
    df = pd.read_parquet(RAW / "r2000_prices.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df


if __name__ == "__main__":
    tickers, sector_map = get_r2000_tickers()
    print(f"downloading {len(tickers)} R2000 tickers {START}..{END}")
    print("(this takes a while; small caps fail more often)")
    df, failed = download_prices(tickers, START, END)
    out = RAW / "r2000_prices.parquet"
    df.to_parquet(out, index=False)
    print(f"saved {out}  ({out.stat().st_size / 1024 / 1024:.1f} MB)")
    # also save the IWM sector map (GICS) for neutralization
    smap = pd.Series(sector_map, name="sector")
    smap.index.name = "ticker"
    smap.to_frame().to_parquet(RAW / "r2000_sectors.parquet")
    print(f"saved sector map: {len(smap)} tickers")