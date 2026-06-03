"""Probe yfinance: can we get daily OHLCV + shares outstanding for a few names?"""
import yfinance as yf
import pandas as pd

tickers = ["AAPL", "MSFT", "JPM", "XOM", "WMT"]

# 1. daily OHLCV
df = yf.download(tickers, start="2018-01-01", end="2024-12-31",
                 auto_adjust=False, group_by="ticker", progress=False)
print("=== price panel shape ===")
print(df.shape)
print("=== columns (AAPL) ===")
print(df["AAPL"].columns.tolist())
print("=== AAPL head ===")
print(df["AAPL"].head(3))
print("=== AAPL tail ===")
print(df["AAPL"].tail(3))

# 2. shares outstanding (for turnover proxy) -- check availability
print("\n=== shares outstanding (current only) ===")
for t in tickers:
    try:
        so = yf.Ticker(t).info.get("sharesOutstanding")
        print(f"{t}: {so}")
    except Exception as e:
        print(f"{t}: ERROR {e}")