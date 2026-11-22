import numpy as np
import pandas as pd
from numpy.polynomial import Polynomial as P
from scipy.optimize import brentq
from scipy.signal import savgol_filter


def divided_difference_table(x, y):
    n = len(x)
    table = np.full((n, n), np.nan)
    table[:, 0] = y
    for j in range(1, n):
        for i in range(n - j):
            table[i, j] = (table[i + 1, j - 1] - table[i, j - 1]) / (x[i + j] - x[i])
    return table


def newton_eval(coef, nodes, t):
    t = np.asarray(t, dtype=float)
    res = np.full_like(t, coef[-1])
    for k in range(len(coef) - 2, -1, -1):
        res = res * (t - nodes[k]) + coef[k]
    return res


def newton_to_poly(coef, nodes):
    p = P([coef[-1]])
    for k in range(len(coef) - 2, -1, -1):
        p = p * P([-nodes[k], 1.0]) + coef[k]
    return p


def newton_raphson(f, df, x0, tol=1e-10, itmax=60):
    x = x0
    for _ in range(itmax):
        d = df(x)
        if abs(d) < 1e-14:
            break
        xn = x - f(x) / d
        if abs(xn - x) < tol:
            return xn
        x = xn
    return x


def poly_zeros(f, df, grid):
    v = f(grid)
    out = []
    for i in np.where(np.sign(v[:-1]) * np.sign(v[1:]) < 0)[0]:
        a, b = grid[i], grid[i + 1]
        r = newton_raphson(f, df, (a + b) / 2)
        if not (a <= r <= b):
            r = brentq(f, a, b)
        out.append(r)
    return np.array(out)


def build_newton(s, n_nodes, node_type):
    days = (s.index - s.index[0]).days.values.astype(float)
    span = days[-1]
    t = 2 * days / span - 1
    y = s.values.astype(float)
    if node_type.startswith("Tcheby"):
        ideal = np.cos(np.pi * np.arange(n_nodes) / (n_nodes - 1))[::-1]
        idx = np.unique(np.abs(t[:, None] - ideal[None, :]).argmin(axis=0))
    else:
        idx = np.unique(np.linspace(0, len(s) - 1, n_nodes).round().astype(int))
    xn, yn = t[idx], y[idx]
    table = divided_difference_table(xn, yn)
    coef = table[0, :]
    return {
        "s": s,
        "days": days,
        "span": span,
        "t": t,
        "y": y,
        "idx": idx,
        "xn": xn,
        "yn": yn,
        "table": table,
        "coef": coef,
        "poly": newton_to_poly(coef, xn),
        "yhat": newton_eval(coef, xn, t),
    }


def t_to_date(r, nw):
    return nw["s"].index[0] + pd.Timedelta(days=float((r + 1) / 2 * nw["span"]))


def date_to_t(d, nw):
    return 2 * (pd.Timestamp(d) - nw["s"].index[0]).days / nw["span"] - 1


def fit_errors(nw):
    err = nw["y"] - nw["yhat"]
    ss_res = (err**2).sum()
    ss_tot = ((nw["y"] - nw["y"].mean()) ** 2).sum()
    return {
        "err": err,
        "rmse": float(np.sqrt((err**2).mean())),
        "max": float(np.abs(err).max()),
        "r2": float(1 - ss_res / ss_tot),
    }


def polynomial_analysis(nw):
    poly = nw["poly"]
    p1, p2, p3 = poly.deriv(1), poly.deriv(2), poly.deriv(3)
    grid = np.linspace(-1, 1, 4001)
    return {
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "inflections": poly_zeros(p2, p3, grid),
        "extrema": poly_zeros(p1, p2, grid),
        "scale1": 2 / nw["span"],
        "scale2": (2 / nw["span"]) ** 2,
    }


def sg_derivatives(s, window, order=3):
    w = min(window, len(s))
    if w % 2 == 0:
        w -= 1
    w = max(w, order + 2 if (order + 2) % 2 == 1 else order + 3)
    v = s.values.astype(float)
    return (
        savgol_filter(v, w, order),
        savgol_filter(v, w, order, deriv=1),
        savgol_filter(v, w, order, deriv=2),
        w,
    )


def sign_changes(arr):
    sg = np.sign(arr)
    return np.where(sg[:-1] * sg[1:] < 0)[0]


def state_text(d1, d2):
    if d1 > 0 and d2 > 0:
        return "Hausse qui s'accélère (f' > 0, f'' > 0)"
    if d1 > 0 and d2 < 0:
        return "Hausse qui ralentit (f' > 0, f'' < 0)"
    if d1 < 0 and d2 > 0:
        return "Baisse qui ralentit (f' < 0, f'' > 0)"
    return "Baisse qui s'accélère (f' < 0, f'' < 0)"


def inflection_label(d2_before, d2_after):
    return "concave → convexe" if d2_before < 0 < d2_after else "convexe → concave"
