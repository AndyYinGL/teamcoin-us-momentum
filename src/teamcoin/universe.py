"""S&P 500 universe: fetch current constituents from Wikipedia."""
import io
import requests
import pandas as pd

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0 Safari/537.36"}


def get_sp500_tickers():
    """Return current S&P 500 tickers as a list, cleaned for yfinance."""
    resp = requests.get(WIKI_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]
    tickers = df["Symbol"].astype(str).str.strip().tolist()
    # yfinance uses '-' not '.' for class shares (e.g. BRK.B -> BRK-B)
    tickers = [t.replace(".", "-") for t in tickers]
    return tickers


if __name__ == "__main__":
    t = get_sp500_tickers()
    print(f"got {len(t)} tickers")
    print("first 10:", t[:10])
    print("any with dash:", [x for x in t if "-" in x][:5])