import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

METALS = {
    "Or": {"yf": "GC=F", "stooq": "xauusd", "pair": "XAU/USD"},
    "Argent": {"yf": "SI=F", "stooq": "xagusd", "pair": "XAG/USD"},
}


def _from_yfinance(ticker, start, end):
    try:
        import yfinance as yf

        d = yf.download(
            ticker,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=False,
        )
        if d is None or d.empty:
            return None
        close = d["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.dropna().astype(float)
        close.index = pd.to_datetime(close.index).tz_localize(None)
        return close
    except Exception:
        return None


def _from_stooq(symbol, start, end):
    try:
        url = f"https://stooq.com/q/d/l/?s={symbol}&i=d&d1={start:%Y%m%d}&d2={end:%Y%m%d}"
        d = pd.read_csv(url, parse_dates=["Date"], index_col="Date")
        s = d["Close"].dropna().astype(float)
        return s if not s.empty else None
    except Exception:
        return None


def _demo_data(years):
    rng = np.random.default_rng(7)
    idx = pd.bdate_range(end=date.today(), periods=int(years * 252))
    gold = 1300 * np.exp(np.cumsum(rng.normal(0.0004, 0.009, len(idx))))
    silver = 17 * np.exp(np.cumsum(0.6 * np.diff(np.log(gold), prepend=0) + rng.normal(0.0001, 0.011, len(idx))))
    return pd.DataFrame({"Or": gold, "Argent": silver}, index=idx)


@st.cache_data(ttl=3600, show_spinner="Téléchargement des prix (API open source)...")
def load_prices(years=10):
    if os.environ.get("GOLD_APP_DEMO") == "1":
        return _demo_data(years), {"Or": "Démo synthétique", "Argent": "Démo synthétique"}
    end = date.today()
    start = end - timedelta(days=int(365.25 * years) + 10)
    frames, sources = {}, {}
    for name, cfg in METALS.items():
        series, src = _from_yfinance(cfg["yf"], start, end), "Yahoo Finance (yfinance)"
        if series is None or series.empty:
            series, src = _from_stooq(cfg["stooq"], start, end), "Stooq (CSV ouvert)"
        if series is not None and not series.empty:
            frames[name], sources[name] = series, src
    if len(frames) < 2:
        return pd.DataFrame(), sources
    df = pd.DataFrame(frames).sort_index().ffill().dropna()
    return df, sources


def last_year(df):
    return df.loc[df.index >= df.index[-1] - pd.DateOffset(years=1)]
