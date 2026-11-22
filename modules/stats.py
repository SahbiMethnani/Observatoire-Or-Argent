import numpy as np
import pandas as pd

TRADING_DAYS = 252


def log_returns(df):
    return np.log(df).diff().dropna()


def max_drawdown(s):
    return (s / s.cummax() - 1).min()


def drawdown_series(s):
    return (s / s.cummax() - 1) * 100


def rsi(s, n=14):
    delta = s.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / down)


def rolling_volatility(s, window=30):
    return np.log(s).diff().rolling(window).std() * np.sqrt(TRADING_DAYS) * 100


def bollinger(s, window=20, k=2.0):
    ma = s.rolling(window).mean()
    sd = s.rolling(window).std()
    return ma, ma + k * sd, ma - k * sd


def annual_table(s):
    rows = []
    for yr, g in s.groupby(s.index.year):
        lr = np.log(g).diff().dropna()
        rows.append(
            {
                "Année": yr,
                "Ouverture": g.iloc[0],
                "Clôture": g.iloc[-1],
                "Min": g.min(),
                "Max": g.max(),
                "Rendement %": (g.iloc[-1] / g.iloc[0] - 1) * 100,
                "Volatilité ann. %": lr.std() * np.sqrt(TRADING_DAYS) * 100,
                "Drawdown max %": max_drawdown(g) * 100,
            }
        )
    return pd.DataFrame(rows).set_index("Année").round(2)


def monthly_returns(s):
    try:
        m = s.resample("ME").last()
    except ValueError:
        m = s.resample("M").last()
    r = m.pct_change().dropna() * 100
    t = pd.DataFrame({"Année": r.index.year, "Mois": r.index.month, "r": r.values})
    return t.pivot(index="Année", columns="Mois", values="r")


def ten_year_kpi(df, returns):
    years = (df.index[-1] - df.index[0]).days / 365.25
    out = {}
    for m in df.columns:
        out[m] = {
            "Prix initial": f"{df[m].iloc[0]:,.2f}",
            "Prix final": f"{df[m].iloc[-1]:,.2f}",
            "Plus haut": f"{df[m].max():,.2f}",
            "Date plus haut": str(df[m].idxmax().date()),
            "Plus bas": f"{df[m].min():,.2f}",
            "Date plus bas": str(df[m].idxmin().date()),
            "TCAM %": f"{((df[m].iloc[-1] / df[m].iloc[0]) ** (1 / years) - 1) * 100:.2f}",
            "Volatilité annualisée %": f"{returns[m].std() * np.sqrt(TRADING_DAYS) * 100:.2f}",
            "Drawdown maximal %": f"{max_drawdown(df[m]) * 100:.2f}",
        }
    return pd.DataFrame(out)


def year_description(prices, returns):
    desc = pd.DataFrame({"Prix": prices.describe(), "Rendement journalier %": (returns * 100).describe()})
    desc.loc["asymétrie (skew)", "Rendement journalier %"] = returns.skew()
    desc.loc["kurtosis", "Rendement journalier %"] = returns.kurt()
    return desc.round(3)


def matrix_stats(R):
    X = R.values
    cov_m = np.cov(X, rowvar=False) * TRADING_DAYS
    cor_m = np.corrcoef(X, rowvar=False)
    cov_df = pd.DataFrame(cov_m, index=R.columns, columns=R.columns)
    cor_df = pd.DataFrame(cor_m, index=R.columns, columns=R.columns)
    vals, vecs = np.linalg.eigh(cov_m)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    names = [f"CP{i + 1}" for i in range(len(vals))]
    pca = pd.DataFrame(
        {"Valeur propre": vals, "Variance expliquée %": vals / vals.sum() * 100},
        index=names,
    )
    vec_df = pd.DataFrame(vecs, index=R.columns, columns=names)
    return {
        "cov": cov_df,
        "cor": cor_df,
        "pca": pca,
        "vec": vec_df,
        "det": float(np.linalg.det(cov_m)),
        "trace": float(np.trace(cov_m)),
        "cond": float(vals[0] / vals[-1]),
    }


def return_summary(R):
    return pd.DataFrame(
        {
            "Moyenne %": R.mean() * 100,
            "Écart-type %": R.std() * 100,
            "Asymétrie": R.skew(),
            "Kurtosis": R.kurt(),
            "Min %": R.min() * 100,
            "Max %": R.max() * 100,
            "VaR 95 % (jour) %": R.quantile(0.05) * 100,
        }
    ).T
