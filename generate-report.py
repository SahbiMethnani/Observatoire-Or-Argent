import argparse
import io
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from modules.data import last_year, load_prices

COLORS = {"Or": "#C9A227", "Argent": "#7F8C8D"}
UNITS = {"Or": "USD/once", "Argent": "USD/once"}



def max_drawdown(s):
    peak = s.cummax()
    return float((s / peak - 1).min())


def basic_stats(s):
    r = s.pct_change().dropna()
    days = (s.index[-1] - s.index[0]).days
    cagr = (s.iloc[-1] / s.iloc[0]) ** (365.25 / max(days, 1)) - 1
    return {
        "Dernier prix": s.iloc[-1],
        "Premier prix": s.iloc[0],
        "Minimum": s.min(),
        "Maximum": s.max(),
        "Moyenne": s.mean(),
        "Médiane": s.median(),
        "Variation totale (%)": (s.iloc[-1] / s.iloc[0] - 1) * 100,
        "Rendement annualisé (%)": cagr * 100,
        "Volatilité annualisée (%)": r.std() * np.sqrt(252) * 100,
        "Perte max. (drawdown, %)": max_drawdown(s) * 100,
    }


def yearly_returns(df):
    last = df.groupby(df.index.year).last()
    first = df.groupby(df.index.year).first()
    out = (last / first - 1) * 100
    out.index.name = "Année"
    return out


def newton_divided_differences(x, y):
    n = len(x)
    table = np.zeros((n, n))
    table[:, 0] = y
    for j in range(1, n):
        for i in range(n - j):
            table[i, j] = (table[i + 1, j - 1] - table[i, j - 1]) / (x[i + j] - x[i])
    return table


def newton_eval(x_nodes, coeffs, xq):
    res = np.full_like(xq, coeffs[-1], dtype=float)
    for k in range(len(coeffs) - 2, -1, -1):
        res = res * (xq - x_nodes[k]) + coeffs[k]
    return res


def newton_interpolation(s, n_nodes=8):
    
    n = len(s)
    idx = np.linspace(0, n - 1, n_nodes).round().astype(int)
    x_all = np.linspace(0, 1, n)
    xn, yn = x_all[idx], s.values[idx]
    table = newton_divided_differences(xn, yn)
    coeffs = table[0, :]
    fit = newton_eval(xn, coeffs, x_all)
    err = fit - s.values
    return {
        "idx": idx,
        "x_nodes": xn,
        "y_nodes": yn,
        "table": table,
        "coeffs": coeffs,
        "fit": pd.Series(fit, index=s.index),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mape": float(np.mean(np.abs(err / s.values)) * 100),
        "max_err": float(np.max(np.abs(err))),
        "degree": n_nodes - 1,
    }


def derivatives(s, window=21):
    smooth = s.rolling(window, center=True, min_periods=1).mean()
    d1 = pd.Series(np.gradient(smooth.values), index=s.index)
    d1s = d1.rolling(window, center=True, min_periods=1).mean()
    d2 = pd.Series(np.gradient(d1s.values), index=s.index)
    return smooth, d1s, d2


def inflection_points(s, window=21, min_gap=15):
    smooth, d1, d2 = derivatives(s, window)
    d2s = d2.rolling(window, center=True, min_periods=1).mean()
    sign = np.sign(d2s.values)
    pts, last_i = [], -10**9
    for i in range(1, len(sign)):
        if sign[i] != 0 and sign[i - 1] != 0 and sign[i] != sign[i - 1] and i - last_i >= min_gap:
            kind = "concave → convexe" if sign[i] > 0 else "convexe → concave"
            pts.append({"Date": s.index[i], "Prix": float(s.iloc[i]), "Type": kind,
                        "Pente": float(d1.iloc[i])})
            last_i = i
    return pts


def trend_state(d1, d2):
    p, a = d1.iloc[-1], d2.iloc[-1]
    if p > 0 and a > 0:
        return "hausse qui s'accélère"
    if p > 0:
        return "hausse qui ralentit"
    if a < 0:
        return "baisse qui s'accélère"
    return "baisse qui ralentit"



def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _style(ax, title, ylabel=None):
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.grid(alpha=0.25)
    if ylabel:
        ax.set_ylabel(ylabel)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def chart_10y(df):
    fig, axes = plt.subplots(2, 1, figsize=(8, 5.5), sharex=True)
    for ax, m in zip(axes, ["Or", "Argent"]):
        ax.plot(df.index, df[m], color=COLORS[m], lw=1.2)
        ax.fill_between(df.index, df[m], df[m].min(), color=COLORS[m], alpha=0.12)
        _style(ax, f"{m} — 10 ans", UNITS[m])
    fig.tight_layout()
    return _png(fig)


def chart_base100(df):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    b = df / df.iloc[0] * 100
    for m in b.columns:
        ax.plot(b.index, b[m], color=COLORS[m], lw=1.3, label=m)
    ax.legend(frameon=False)
    _style(ax, "Performance comparée (base 100)")
    return _png(fig)


def chart_ratio(df):
    ratio = df["Or"] / df["Argent"]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(ratio.index, ratio, color="#34495E", lw=1.1)
    ax.axhline(ratio.mean(), color="red", ls="--", lw=0.9, label=f"moyenne = {ratio.mean():.1f}")
    ax.legend(frameon=False)
    _style(ax, "Ratio Or / Argent")
    return _png(fig)


def chart_corr(corr):
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    im = ax.imshow(corr.values, cmap="YlOrBr", vmin=0, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns)
    ax.set_yticks(range(len(corr)), corr.index)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=10)
    fig.colorbar(im, fraction=0.046)
    ax.set_title("Corrélation des rendements", fontsize=10, fontweight="bold")
    return _png(fig)


def chart_inflection(s, metal, pts):
    smooth, _, _ = derivatives(s)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(s.index, s, color=COLORS[metal], lw=0.9, alpha=0.6, label="Prix")
    ax.plot(smooth.index, smooth, color="black", lw=1.4, label="Lissé (21 j)")
    if pts:
        ax.scatter([p["Date"] for p in pts], [p["Prix"] for p in pts], color="red",
                   zorder=5, s=40, label="Points d'inflexion")
    ax.legend(frameon=False, fontsize=8)
    _style(ax, f"{metal} — dernière année et points d'inflexion", UNITS[metal])
    fig.autofmt_xdate()
    return _png(fig)


def chart_derivatives(s, metal):
    _, d1, d2 = derivatives(s)
    fig, axes = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True)
    axes[0].plot(d1.index, d1, color="#2980B9", lw=1.1)
    axes[0].axhline(0, color="black", lw=0.7)
    _style(axes[0], f"{metal} — dérivée première (pente par jour)")
    axes[1].plot(d2.index, d2, color="#C0392B", lw=1.1)
    axes[1].axhline(0, color="black", lw=0.7)
    _style(axes[1], "Dérivée seconde (accélération)")
    fig.autofmt_xdate()
    fig.tight_layout()
    return _png(fig)


def chart_newton(s, metal, res):
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(s.index, s, color=COLORS[metal], lw=1.1, label="Prix réel")
    ax.plot(res["fit"].index, res["fit"], color="#C0392B", lw=1.4, ls="--",
            label=f"Polynôme de Newton (degré {res['degree']})")
    ax.scatter(s.index[res["idx"]], res["y_nodes"], color="black", zorder=5, s=30, label="Nœuds")
    lo, hi = s.min(), s.max()
    pad = (hi - lo) * 0.3
    ax.set_ylim(lo - pad, hi + pad)
    ax.legend(frameon=False, fontsize=8)
    _style(ax, f"{metal} — interpolation de Newton", UNITS[metal])
    fig.autofmt_xdate()
    return _png(fig)

def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_table(doc, header, rows, widths=None, font=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.size = Pt(font)
        run.font.color.rgb = RGBColor(255, 255, 255)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _shade(c, "1F3A5F")
    for r_i, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            run = p.add_run(str(v))
            run.font.size = Pt(font)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.RIGHT
            if r_i % 2:
                _shade(cells[i], "F2F5F9")
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def add_figure(doc, buf, caption, width=15.5):
    doc.add_picture(buf, width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(caption)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].italic = True
    p.runs[0].font.size = Pt(9)


def para(doc, text, bold=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    p.paragraph_format.space_after = Pt(6)
    return p


def fmt(x, nd=2):
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


def fdate(d):
    return pd.Timestamp(d).strftime("%d/%m/%Y")



def build_report(df, sources=None, n_nodes=8, as_bytes=True):
    sources = sources or {}
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2.2)
    st_normal = doc.styles["Normal"]
    st_normal.font.name = "Calibri"
    st_normal.font.size = Pt(11)

    ly = last_year(df)
    corr = df.pct_change().dropna().corr()
    cov = df.pct_change().dropna().cov() * 252
    corr_ly = ly.pct_change().dropna().corr()
    ratio = df["Or"] / df["Argent"]

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Rapport d'analyse des marchés\nOr & Argent")
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run(f"Période : {fdate(df.index[0])} → {fdate(df.index[-1])}\n"
                f"Généré le {date.today():%d/%m/%Y}").italic = True
    src_txt = ", ".join(sorted(set(sources.values()))) or "non précisée"
    para(doc, f"Source des données : {src_txt}.")

    doc.add_heading("1. Synthèse", 1)
    for m in ["Or", "Argent"]:
        s10, s1 = df[m], ly[m]
        sm, d1, d2 = derivatives(s1)
        para(doc,
             f"{m} : dernier prix {fmt(s10.iloc[-1])} USD, soit {fmt((s10.iloc[-1]/s10.iloc[0]-1)*100, 1)} % "
             f"sur la période et {fmt((s1.iloc[-1]/s1.iloc[0]-1)*100, 1)} % sur la dernière année. "
             f"Tendance actuelle (dérivées lissées) : {trend_state(d1, d2)}.")
    para(doc, f"Corrélation des rendements journaliers Or/Argent : {fmt(corr.loc['Or','Argent'])} "
              f"(sur la dernière année : {fmt(corr_ly.loc['Or','Argent'])}). "
              f"Ratio Or/Argent actuel : {fmt(ratio.iloc[-1], 1)} (moyenne : {fmt(ratio.mean(), 1)}).")

    doc.add_heading("2. Analyse sur 10 ans", 1)
    add_figure(doc, chart_10y(df), "Figure 1 — Évolution des prix sur 10 ans")
    stats = {m: basic_stats(df[m]) for m in ["Or", "Argent"]}
    rows = [[k, fmt(stats["Or"][k]), fmt(stats["Argent"][k])] for k in stats["Or"]]
    add_table(doc, ["Indicateur", "Or", "Argent"], rows, widths=[7, 4, 4])
    add_figure(doc, chart_base100(df), "Figure 2 — Performance comparée (base 100)")

    doc.add_heading("Rendement par année civile (%)", 2)
    yr = yearly_returns(df)
    rows = [[int(y), fmt(yr.loc[y, "Or"], 1), fmt(yr.loc[y, "Argent"], 1)] for y in yr.index]
    add_table(doc, ["Année", "Or", "Argent"], rows, widths=[4, 4, 4])
    para(doc, f"Meilleure année pour l'or : {int(yr['Or'].idxmax())} ({fmt(yr['Or'].max(),1)} %) ; "
              f"pour l'argent : {int(yr['Argent'].idxmax())} ({fmt(yr['Argent'].max(),1)} %). "
              "La dernière année civile est partielle.")

    doc.add_heading("3. Statistiques matricielles", 1)
    para(doc, "Matrices calculées sur les rendements journaliers (covariance annualisée ×252).")
    add_table(doc, ["Covariance annualisée", "Or", "Argent"],
              [[i, fmt(cov.loc[i, "Or"], 5), fmt(cov.loc[i, "Argent"], 5)] for i in cov.index],
              widths=[6, 4, 4])
    add_table(doc, ["Corrélation (10 ans)", "Or", "Argent"],
              [[i, fmt(corr.loc[i, "Or"], 3), fmt(corr.loc[i, "Argent"], 3)] for i in corr.index],
              widths=[6, 4, 4])
    eigvals = np.linalg.eigvalsh(cov.values)[::-1]
    para(doc, f"Valeurs propres de la matrice de covariance : {fmt(eigvals[0], 5)} et {fmt(eigvals[1], 5)}. "
              f"La première composante principale explique {fmt(eigvals[0]/eigvals.sum()*100, 1)} % de la variance totale : "
              "les deux métaux évoluent largement ensemble.")
    add_figure(doc, chart_corr(corr), "Figure 3 — Matrice de corrélation", width=8)
    add_figure(doc, chart_ratio(df), "Figure 4 — Ratio Or / Argent")

    doc.add_heading("4. Analyse approfondie de la dernière année", 1)
    rows = []
    for k in stats["Or"]:
        a, b = basic_stats(ly["Or"])[k], basic_stats(ly["Argent"])[k]
        rows.append([k, fmt(a), fmt(b)])
    add_table(doc, ["Indicateur (dernière année)", "Or", "Argent"], rows, widths=[7, 4, 4])

    doc.add_heading("5. Interpolation de Newton", 1)
    para(doc, "Le polynôme de Newton s'écrit P(x) = a₀ + a₁(x−x₀) + a₂(x−x₀)(x−x₁) + … où les "
              "coefficients aₖ sont les différences divisées f[x₀,…,xₖ]. L'axe du temps est normalisé "
              f"dans [0, 1] et {n_nodes} nœuds équidistants (degré {n_nodes-1}) sont utilisés.")
    for m in ["Or", "Argent"]:
        res = newton_interpolation(ly[m], n_nodes)
        doc.add_heading(m, 2)
        add_table(doc, ["k", "xₖ (normalisé)", "Prix (nœud)", "Coefficient aₖ"],
                  [[k, fmt(res["x_nodes"][k], 4), fmt(res["y_nodes"][k]), fmt(res["coeffs"][k], 2)]
                   for k in range(n_nodes)], widths=[1.5, 4, 4, 4.5])
        add_figure(doc, chart_newton(ly[m], m, res), f"Figure — Interpolation de Newton ({m})")
        para(doc, f"Qualité de l'ajustement : RMSE = {fmt(res['rmse'])} USD ; erreur relative moyenne = "
                  f"{fmt(res['mape'])} % ; erreur maximale = {fmt(res['max_err'])} USD. "
                  "Un polynôme de degré élevé reproduit bien les nœuds mais peut osciller entre eux "
                  "(phénomène de Runge) : il sert à l'interpolation, pas à la prévision.")

    doc.add_heading("6. Dérivées et points d'inflexion", 1)
    para(doc, "La courbe est lissée (moyenne mobile 21 jours) ; la dérivée première donne la pente "
              "(variation de prix par jour) et la dérivée seconde la courbure. Un point d'inflexion "
              "correspond à un changement de signe de la dérivée seconde.")
    for m in ["Or", "Argent"]:
        s1 = ly[m]
        _, d1, d2 = derivatives(s1)
        pts = inflection_points(s1)
        doc.add_heading(m, 2)
        add_figure(doc, chart_inflection(s1, m, pts), f"Figure — {m} : points d'inflexion")
        add_figure(doc, chart_derivatives(s1, m), f"Figure — {m} : dérivées première et seconde")
        if pts:
            add_table(doc, ["Date", "Prix", "Pente (USD/j)", "Changement"],
                      [[fdate(p["Date"]), fmt(p["Prix"]), fmt(p["Pente"], 3), p["Type"]] for p in pts],
                      widths=[3.5, 3.5, 3.5, 5])
        else:
            para(doc, "Aucun point d'inflexion détecté sur la période.")
        para(doc, f"État actuel : pente = {fmt(d1.iloc[-1], 3)} USD/jour, courbure = {fmt(d2.iloc[-1], 4)} "
                  f"→ {trend_state(d1, d2)}.")

    doc.add_heading("7. Conclusion", 1)
    para(doc, "Ce rapport est généré automatiquement à partir de données de marché ouvertes. "
              "Les méthodes numériques (interpolation, dérivées) décrivent le passé et ne constituent "
              "ni une prévision ni un conseil en investissement.")

    if as_bytes:
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    return doc


def gen_rapport():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="rapport_or_argent.docx")
    ap.add_argument("--nodes", type=int, default=8, help="nombre de nœuds de Newton")
    args = ap.parse_args()
    df, sources = load_prices(10)
    if df.empty:
        raise SystemExit("Impossible de récupérer les prix (vérifiez la connexion).")
    data = build_report(df, sources, n_nodes=args.nodes)
    with open(args.output, "wb") as f:
        f.write(data)
    print(f"Rapport généré : {args.output}")

"""
if __name__ == "__main__":
    main()
"""