"""Download and cache daily OHLCV for the S&P 500 universe via yfinance."""
import time
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path.home() / "teamcoin-us-momentum"
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

START = "2018-01-01"
END = "2024-12-31"
BATCH = 50            # tickers per download call
PAUSE = 1.0           # seconds between batches (be gentle with yfinance)


def download_prices(tickers, start=START, end=END):
    """Download OHLCV for all tickers in batches; return a long DataFrame
    with columns [date, ticker, open, high, low, close, adj_close, volume]."""
    frames = []
    failed = []
    for i in range(0, len(tickers), BATCH):
        batch = tickers[i:i + BATCH]
        print(f"  batch {i // BATCH + 1}: {batch[0]}..{batch[-1]} ({len(batch)} tickers)")
        try:
            raw = yf.download(batch, start=start, end=end, auto_adjust=False,
                              group_by="ticker", progress=False, threads=True)
        except Exception as e:
            print(f"    batch error: {e}")
            failed.extend(batch)
            continue
        for t in batch:
            try:
                sub = raw[t].dropna(how="all").copy()
                if sub.empty:
                    failed.append(t)
                    continue
                sub = sub.reset_index()
                sub.columns = [str(c).lower().replace(" ", "_") for c in sub.columns]
                sub["ticker"] = t
                frames.append(sub)
            except Exception:
                failed.append(t)
        time.sleep(PAUSE)

    df = pd.concat(frames, ignore_index=True)
    df = df.rename(columns={"adj_close": "adj_close"})
    print(f"\ngot {df['ticker'].nunique()} tickers, {len(df)} rows")
    if failed:
        print(f"failed ({len(failed)}): {failed}")
    return df, failed

def load_prices():
    """Load cached long price table from parquet."""
    df = pd.read_parquet(RAW / "sp500_prices.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df


def to_panel(df, field="adj_close"):
    """Pivot long table to a date x ticker panel for one field."""
    return df.pivot(index="date", columns="ticker", values=field).sort_index()

if __name__ == "__main__":
    from teamcoin.universe import get_sp500_tickers
    tickers = get_sp500_tickers()
    print(f"downloading {len(tickers)} tickers {START}..{END}")
    df, failed = download_prices(tickers)
    out = RAW / "sp500_prices.parquet"
    df.to_parquet(out, index=False)
    print(f"saved {out}  ({out.stat().st_size / 1024 / 1024:.1f} MB)")