"""Russell 2000 universe from the iShares IWM holdings CSV.

The CSV has 8 metadata lines, then a header row (Ticker, Name, Sector,
Asset Class, ...), then holdings. We keep only equity holdings with a valid
US ticker, and clean tickers for yfinance (.  -> -)."""
from pathlib import Path
import pandas as pd

ROOT = Path.home() / "teamcoin-us-momentum"
RAW = ROOT / "data" / "raw"
IWM_CSV = RAW / "iwm_holdings.csv"


def get_r2000_tickers():
    """Parse IWM holdings CSV -> cleaned equity ticker list + sector map."""
    # header is on line 9 (0-indexed 8): skip first 8 metadata rows
    df = pd.read_csv(IWM_CSV, skiprows=8)
    # keep only equities
    df = df[df["Asset Class"].astype(str).str.strip() == "Equity"].copy()
    # ticker cleaning
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.replace(".", "-", regex=False)
    # drop cash/derivative/blank rows
    bad = {"", "-", "NAN", "USD", "CASH"}
    df = df[~df["Ticker"].str.upper().isin(bad)]
    # some IWM rows are non-tradeable placeholders; keep plausible tickers only
    df = df[df["Ticker"].str.match(r"^[A-Z][A-Z0-9-]{0,6}$")]
    tickers = df["Ticker"].tolist()
    sector_map = df.set_index("Ticker")["Sector"].to_dict()
    return tickers, sector_map


if __name__ == "__main__":
    tickers, sector = get_r2000_tickers()
    print(f"got {len(tickers)} equity tickers")
    print("first 10:", tickers[:10])
    print("any with dash:", [t for t in tickers if "-" in t][:5])
    print("\nsector counts (top):")
    sc = pd.Series(sector).value_counts()
    print(sc.head(15))