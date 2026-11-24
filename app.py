import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from lire_analyse import display_docx

from modules import theme
from modules import data, numerics, stats

st.set_page_config(page_title="Or & Argent | Marchés", page_icon="◆", layout="wide")
theme.register_plotly_theme()
theme.inject_css()

TD = stats.TRADING_DAYS


def sidebar():
    with st.sidebar:
        st.header("Paramètres")
        metal = st.selectbox("Métal (interpolation et dérivées)", list(data.METALS))
        n_nodes = st.slider("Nombre de nœuds de Newton", 4, 25, 12)
        node_type = st.radio("Répartition des nœuds", ["Tchebychev (recommandé)", "Équidistants"])
        win = st.slider("Fenêtre de lissage Savitzky-Golay (jours)", 11, 101, 31, step=2)
        if st.button("Rafraîchir les données"):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        st.caption(
            "Sources : Yahoo Finance via yfinance (GC=F, SI=F), repli Stooq. Prix en USD par once troy "
            "(contrats à terme continus). Ne constitue pas un conseil en investissement."
        )
    return metal, n_nodes, node_type, win


def header(df, df1, sources):
    st.markdown(theme.brand_html(), unsafe_allow_html=True)
    items = []
    for m, cfg in data.METALS.items():
        last, prev = df[m].iloc[-1], df[m].iloc[-2]
        items.append((cfg["pair"], f"{last:,.2f}", (last / prev - 1) * 100))
    for m in data.METALS:
        items.append((f"{m} 12 m", "", (df1[m].iloc[-1] / df1[m].iloc[0] - 1) * 100))
    items.append(("Ratio Or/Argent", f"{df['Or'].iloc[-1] / df['Argent'].iloc[-1]:.2f}", None))
    st.markdown(theme.ticker_html(items), unsafe_allow_html=True)

    cols = st.columns(4)
    for i, m in enumerate(data.METALS):
        last, prev = df[m].iloc[-1], df[m].iloc[-2]
        cols[2 * i].metric(f"{m} - dernier prix", f"{last:,.2f} $", f"{(last / prev - 1) * 100:+.2f} % (jour)")
        cols[2 * i + 1].metric(
            f"{m} - 12 mois",
            f"{(df1[m].iloc[-1] / df1[m].iloc[0] - 1) * 100:+.1f} %",
            f"10 ans : {(df[m].iloc[-1] / df[m].iloc[0] - 1) * 100:+.0f} %",
        )
    st.caption(
        f"Données du {df.index[0]:%d/%m/%Y} au {df.index[-1]:%d/%m/%Y} - {len(df)} séances. "
        f"Sources : Or = {sources.get('Or')}, Argent = {sources.get('Argent')}."
    )


def tab_overview(df, ret10):
    a, b = st.columns(2)
    a.plotly_chart(theme.line_fig(df["Or"], "Or - 10 ans", theme.METAL_COLORS["Or"]), width="stretch")
    b.plotly_chart(theme.line_fig(df["Argent"], "Argent - 10 ans", theme.METAL_COLORS["Argent"]), width="stretch")

    base = df / df.iloc[0] * 100
    fig = go.Figure()
    for m in data.METALS:
        fig.add_trace(go.Scatter(x=base.index, y=base[m], name=m, line=dict(color=theme.METAL_COLORS[m], width=2)))
    fig.update_layout(title="Performance comparée (base 100 il y a 10 ans)", height=380)
    st.plotly_chart(fig, width="stretch")

    ratio = df["Or"] / df["Argent"]
    fr = theme.line_fig(ratio, "Ratio Or / Argent", theme.VIOLET, "ratio")
    fr.add_hline(y=ratio.mean(), line_dash="dash", line_color=theme.MUTED, annotation_text=f"moyenne {ratio.mean():.1f}")
    st.plotly_chart(fr, width="stretch")

    st.subheader("Bilan annuel")
    a, b = st.columns(2)
    a.markdown("**Or**")
    a.dataframe(stats.annual_table(df["Or"]), width="stretch")
    b.markdown("**Argent**")
    b.dataframe(stats.annual_table(df["Argent"]), width="stretch")

    st.subheader("Indicateurs sur 10 ans")
    st.dataframe(stats.ten_year_kpi(df, ret10), width="stretch")


def tab_year(df, df1, ret1):
    st.subheader(f"Analyse approfondie - 12 derniers mois ({df1.index[0]:%d/%m/%Y} → {df1.index[-1]:%d/%m/%Y})")
    mm = st.radio("Métal", list(data.METALS), horizontal=True, key="m_year")
    full = df[mm]
    ma20, upper, lower = stats.bollinger(full, 20)
    ma50, ma200 = full.rolling(50).mean(), full.rolling(200).mean()
    sl = full.index >= df1.index[0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=full.index[sl], y=upper[sl], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(
        go.Scatter(
            x=full.index[sl],
            y=lower[sl],
            fill="tonexty",
            line=dict(width=0),
            fillcolor="rgba(240,185,11,0.08)",
            name="Bollinger 20j (±2σ)",
            hoverinfo="skip",
        )
    )
    fig.add_trace(go.Scatter(x=full.index[sl], y=full[sl], name="Prix", line=dict(color=theme.METAL_COLORS[mm], width=2.5)))
    for nm, ser, col in (("MM 20", ma20, theme.BLUE), ("MM 50", ma50, theme.VIOLET), ("MM 200", ma200, theme.RED)):
        fig.add_trace(go.Scatter(x=full.index[sl], y=ser[sl], name=nm, line=dict(color=col, width=1.2)))
    fig.update_layout(title=f"{mm} - prix, moyennes mobiles et bandes de Bollinger", height=450)
    st.plotly_chart(fig, width="stretch")

    s1, r1 = df1[mm], ret1[mm]
    k = st.columns(5)
    k[0].metric("Plus haut 12 m", f"{s1.max():,.2f}", f"{s1.idxmax():%d/%m/%y}", delta_color="off")
    k[1].metric("Plus bas 12 m", f"{s1.min():,.2f}", f"{s1.idxmin():%d/%m/%y}", delta_color="off")
    k[2].metric("Volatilité ann.", f"{r1.std() * np.sqrt(TD) * 100:.1f} %")
    k[3].metric("Drawdown max", f"{stats.max_drawdown(s1) * 100:.1f} %")
    k[4].metric("RSI (14)", f"{stats.rsi(full).iloc[-1]:.0f}")

    a, b = st.columns(2)
    dd = stats.drawdown_series(s1)
    fd = go.Figure(go.Scatter(x=dd.index, y=dd, fill="tozeroy", line=dict(color=theme.RED), fillcolor="rgba(246,70,93,0.2)"))
    fd.update_layout(title="Drawdown (%)", height=320)
    a.plotly_chart(fd, width="stretch")
    fh = px.histogram(r1 * 100, nbins=40, title="Distribution des rendements journaliers (%)", color_discrete_sequence=[theme.YELLOW])
    fh.update_layout(height=320, showlegend=False)
    b.plotly_chart(fh, width="stretch")

    a, b = st.columns(2)
    vol = stats.rolling_volatility(full, 30)
    a.plotly_chart(theme.line_fig(vol[sl], "Volatilité glissante 30 j (% annualisé)", theme.BLUE, "%", 320), width="stretch")
    fr = theme.line_fig(stats.rsi(full)[sl], "RSI 14 jours", theme.VIOLET, "RSI", 320)
    fr.add_hrect(y0=70, y1=100, fillcolor=theme.RED, opacity=0.1, line_width=0)
    fr.add_hrect(y0=0, y1=30, fillcolor=theme.GREEN, opacity=0.1, line_width=0)
    b.plotly_chart(fr, width="stretch")

    st.plotly_chart(
        theme.heat(stats.monthly_returns(full), "Rendements mensuels (%) - toutes années", kind="diverging", height=420, decimals=".1f"),
        width="stretch",
    )

    st.markdown("**Statistiques descriptives (12 mois)**")
    st.dataframe(stats.year_description(s1, r1), width="stretch")


def tab_matrices(ret10, ret1):
    st.subheader("Statistiques matricielles sur les rendements logarithmiques")
    per = st.radio("Période", ["10 ans", "12 derniers mois"], horizontal=True)
    R = ret10 if per == "10 ans" else ret1
    ms = stats.matrix_stats(R)

    a, b = st.columns(2)
    a.plotly_chart(theme.heat(ms["cov"], "Matrice de covariance (annualisée)", kind="cov"), width="stretch")
    b.plotly_chart(theme.heat(ms["cor"], "Matrice de corrélation", kind="corr", decimals=".3f"), width="stretch")

    a, b = st.columns(2)
    a.markdown("**Valeurs propres de la covariance (ACP)**")
    a.dataframe(ms["pca"].round(6), width="stretch")
    b.markdown("**Vecteurs propres**")
    b.dataframe(ms["vec"].round(4), width="stretch")

    k = st.columns(4)
    k[0].metric("Déterminant", f"{ms['det']:.3e}")
    k[1].metric("Trace", f"{ms['trace']:.4f}")
    k[2].metric("Conditionnement", f"{ms['cond']:.2f}")
    k[3].metric("Corrélation Or/Argent", f"{ms['cor'].iloc[0, 1]:.3f}")

    st.markdown("**Résumé statistique par métal (rendements journaliers)**")
    st.dataframe(stats.return_summary(R).round(4), width="stretch")

    roll = ret10["Or"].rolling(60).corr(ret10["Argent"]).dropna()
    st.plotly_chart(theme.line_fig(roll, "Corrélation glissante Or/Argent (60 séances)", theme.VIOLET, "corrélation"), width="stretch")

    st.markdown(f"**Matrice des rendements (aperçu des {min(10, len(R))} dernières séances, en %)**")
    st.dataframe((R.tail(10) * 100).round(3), width="stretch")


def tab_newton(nw, metal, node_type, n_nodes):
    st.subheader(f"Interpolation de Newton - {metal}, 12 derniers mois")
    st.latex(r"P(t)=c_0+c_1(t-x_0)+c_2(t-x_0)(t-x_1)+\dots+c_{n}\prod_{i=0}^{n-1}(t-x_i),\quad c_k=f[x_0,\dots,x_k]")
    fe = numerics.fit_errors(nw)
    k = st.columns(5)
    k[0].metric("Nœuds utilisés", len(nw["idx"]))
    k[1].metric("Degré du polynôme", len(nw["idx"]) - 1)
    k[2].metric("RMSE", f"{fe['rmse']:.2f}")
    k[3].metric("Erreur max", f"{fe['max']:.2f}")
    k[4].metric("R²", f"{fe['r2']:.4f}")

    s = nw["s"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=nw["y"], name="Prix réel", line=dict(color=theme.METAL_COLORS[metal], width=2)))
    fig.add_trace(go.Scatter(x=s.index, y=nw["yhat"], name="Polynôme de Newton P(t)", line=dict(color=theme.RED, dash="dash", width=2)))
    fig.add_trace(
        go.Scatter(
            x=s.index[nw["idx"]],
            y=nw["yn"],
            mode="markers",
            name="Nœuds",
            marker=dict(size=9, color=theme.TEXT, symbol="diamond", line=dict(color=theme.BG, width=1)),
        )
    )
    lo, hi = nw["y"].min(), nw["y"].max()
    fig.update_yaxes(range=[lo - 0.15 * (hi - lo), hi + 0.15 * (hi - lo)])
    fig.update_layout(height=480, yaxis_title="USD / once")
    st.plotly_chart(fig, width="stretch")

    ferr = go.Figure(go.Scatter(x=s.index, y=fe["err"], fill="tozeroy", line=dict(color=theme.MUTED), fillcolor="rgba(132,142,156,0.2)"))
    ferr.update_layout(title="Erreur d'interpolation (prix - P)", height=280)
    st.plotly_chart(ferr, width="stretch")

    st.markdown("**Coefficients de Newton (différences divisées d'ordre k)**")
    st.dataframe(
        pd.DataFrame(
            {
                "k": range(len(nw["coef"])),
                "Nœud x_k (t normalisé)": nw["xn"],
                "Date du nœud": s.index[nw["idx"]].date,
                "Prix f(x_k)": nw["yn"],
                "c_k = f[x_0..x_k]": nw["coef"],
            }
        ).round(6),
        width="stretch",
        hide_index=True,
    )

    if len(nw["idx"]) <= 15:
        with st.expander("Tableau complet des différences divisées"):
            tb = pd.DataFrame(nw["table"], columns=[f"ordre {j}" for j in range(nw["table"].shape[1])])
            st.dataframe(tb.round(6), width="stretch")

    st.markdown("**Évaluer l'interpolation à une date de l'année écoulée**")
    d_in = st.date_input("Date", value=s.index[-1].date(), min_value=s.index[0].date(), max_value=s.index[-1].date())
    td = numerics.date_to_t(d_in, nw)
    pv = float(nw["poly"](td))
    dv = float(nw["poly"].deriv(1)(td)) * 2 / nw["span"]
    st.info(f"P({d_in}) = {pv:,.2f} USD/once ; pente P'(t) = {dv:+.3f} USD/once/jour.")
    if node_type.startswith("Équi") and n_nodes > 14:
        st.warning(
            "Phénomène de Runge : avec beaucoup de nœuds équidistants, le polynôme oscille aux extrémités. "
            "Les nœuds de Tchebychev corrigent ce problème."
        )


def tab_derivatives(df, df1, nw, metal, win):
    st.subheader("État des dérivées et points d'inflexion")

    rows = []
    for m in data.METALS:
        _, d1m, d2m, _ = numerics.sg_derivatives(df1[m], win)
        rows.append(
            {
                "Métal": m,
                "f' (USD/jour)": d1m[-1],
                "f'' (USD/jour²)": d2m[-1],
                "État actuel": numerics.state_text(d1m[-1], d2m[-1]),
            }
        )
    st.markdown("**État actuel (dernière séance, dérivées lissées)**")
    st.dataframe(pd.DataFrame(rows).set_index("Métal").round(4), width="stretch")

    st.markdown("### A. Dérivées numériques des données (Savitzky-Golay)")
    per = st.radio("Période", ["12 derniers mois", "10 ans"], horizontal=True, key="per_d")
    ser = df1[metal] if per.startswith("12") else df[metal]
    w_use = win if per.startswith("12") else win * 5
    sm, d1, d2, w_eff = numerics.sg_derivatives(ser, w_use)
    ext, inf = numerics.sign_changes(d1), numerics.sign_changes(d2)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=("Prix lissé", "Dérivée première f' (USD/jour)", "Dérivée seconde f'' (USD/jour²)"),
    )
    fig.add_trace(go.Scatter(x=ser.index, y=ser.values, name="Prix", line=dict(color=theme.METAL_COLORS[metal], width=1), opacity=0.45), 1, 1)
    fig.add_trace(go.Scatter(x=ser.index, y=sm, name="Lissé", line=dict(color=theme.TEXT, width=2)), 1, 1)
    fig.add_trace(
        go.Scatter(x=ser.index[inf], y=sm[inf], mode="markers", name="Points d'inflexion", marker=dict(size=10, color=theme.RED, symbol="x")),
        1,
        1,
    )
    fig.add_trace(
        go.Scatter(
            x=ser.index[ext],
            y=sm[ext],
            mode="markers",
            name="Extrema",
            marker=dict(size=9, color=theme.GREEN, symbol="circle-open", line=dict(width=2)),
        ),
        1,
        1,
    )
    fig.add_trace(go.Scatter(x=ser.index, y=d1, name="f'", line=dict(color=theme.BLUE)), 2, 1)
    fig.add_trace(go.Scatter(x=ser.index, y=d2, name="f''", line=dict(color=theme.VIOLET)), 3, 1)
    fig.add_hline(y=0, line_dash="dot", line_color=theme.MUTED, row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color=theme.MUTED, row=3, col=1)
    fig.update_layout(height=760)
    st.plotly_chart(fig, width="stretch")

    st.caption(
        f"Fenêtre effective : {w_eff} séances, polynôme local de degré 3. "
        f"{len(inf)} point(s) d'inflexion et {len(ext)} extremum(s) détectés. "
        "Augmenter la fenêtre élimine les inflexions dues au bruit."
    )
    a, b = st.columns(2)
    a.markdown("**Points d'inflexion (f'' change de signe)**")
    a.dataframe(
        pd.DataFrame(
            {
                "Date": ser.index[inf].date,
                "Prix lissé": sm[inf].round(2),
                "Type": [numerics.inflection_label(d2[i], d2[i + 1]) for i in inf],
            }
        ),
        width="stretch",
        hide_index=True,
    )
    b.markdown("**Extrema (f' change de signe)**")
    b.dataframe(
        pd.DataFrame(
            {
                "Date": ser.index[ext].date,
                "Prix lissé": sm[ext].round(2),
                "Nature": ["maximum local" if d1[i] > 0 > d1[i + 1] else "minimum local" for i in ext],
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown("### B. Dérivées analytiques du polynôme d'interpolation de Newton (12 mois)")
    pa = numerics.polynomial_analysis(nw)
    poly, p1, p2, p3 = nw["poly"], pa["p1"], pa["p2"], pa["p3"]
    infl_t, crit_t = pa["inflections"], pa["extrema"]
    sc1, sc2 = pa["scale1"], pa["scale2"]
    sN = nw["s"]

    figp = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=("P(t) et points d'inflexion", "P'(t) (USD/jour)", "P''(t) (USD/jour²)"),
    )
    figp.add_trace(go.Scatter(x=sN.index, y=nw["y"], name="Prix", line=dict(color=theme.METAL_COLORS[metal], width=1), opacity=0.45), 1, 1)
    figp.add_trace(go.Scatter(x=sN.index, y=nw["yhat"], name="P(t)", line=dict(color=theme.RED, width=2)), 1, 1)
    if len(infl_t):
        figp.add_trace(
            go.Scatter(
                x=[numerics.t_to_date(r, nw) for r in infl_t],
                y=poly(infl_t),
                mode="markers",
                name="Inflexions de P",
                marker=dict(size=11, color=theme.TEXT, symbol="x"),
            ),
            1,
            1,
        )
    figp.add_trace(go.Scatter(x=sN.index, y=p1(nw["t"]) * sc1, name="P'", line=dict(color=theme.BLUE)), 2, 1)
    figp.add_trace(go.Scatter(x=sN.index, y=p2(nw["t"]) * sc2, name="P''", line=dict(color=theme.VIOLET)), 3, 1)
    figp.add_hline(y=0, line_dash="dot", line_color=theme.MUTED, row=2, col=1)
    figp.add_hline(y=0, line_dash="dot", line_color=theme.MUTED, row=3, col=1)
    lo, hi = nw["y"].min(), nw["y"].max()
    figp.update_yaxes(range=[lo - 0.2 * (hi - lo), hi + 0.2 * (hi - lo)], row=1, col=1)
    figp.update_layout(height=760)
    st.plotly_chart(figp, width="stretch")

    a, b = st.columns(2)
    a.markdown("**Inflexions de P (zéros de P'', raffinés par Newton-Raphson)**")
    a.dataframe(
        pd.DataFrame(
            {
                "Date": [numerics.t_to_date(r, nw).date() for r in infl_t],
                "P(t)": poly(infl_t).round(2) if len(infl_t) else [],
                "Type": ["concave → convexe" if p3(r) > 0 else "convexe → concave" for r in infl_t],
            }
        ),
        width="stretch",
        hide_index=True,
    )
    b.markdown("**Extrema de P (zéros de P')**")
    b.dataframe(
        pd.DataFrame(
            {
                "Date": [numerics.t_to_date(r, nw).date() for r in crit_t],
                "P(t)": poly(crit_t).round(2) if len(crit_t) else [],
                "Nature": ["maximum" if p2(r) < 0 else "minimum" for r in crit_t],
            }
        ),
        width="stretch",
        hide_index=True,
    )
    tN = nw["t"][-1]
    st.info(
        f"État de P à la dernière séance : P' = {p1(tN) * sc1:+.3f} USD/jour, P'' = {p2(tN) * sc2:+.4f} USD/jour² → "
        f"{numerics.state_text(p1(tN), p2(tN))}. Attention : les valeurs aux bords du polynôme sont sensibles (effet de bord)."
    )


def tab_method():
    st.subheader("Méthodologie")
    st.markdown(
        "**Données.** Prix de clôture journaliers des contrats à terme continus sur l'or (`GC=F`) et l'argent (`SI=F`), "
        "obtenus via la bibliothèque open source `yfinance`; repli automatique sur les CSV ouverts de Stooq."
    )
    st.markdown("**Rendement logarithmique, volatilité annualisée, covariance annualisée**")
    st.latex(r"r_t=\ln\frac{S_t}{S_{t-1}},\qquad \sigma_{ann}=\sigma_{jour}\sqrt{252},\qquad \Sigma_{ann}=252\cdot\mathrm{Cov}(r)")
    st.markdown("**Différences divisées de Newton**")
    st.latex(r"f[x_i]=f(x_i),\qquad f[x_i,\dots,x_{i+k}]=\frac{f[x_{i+1},\dots,x_{i+k}]-f[x_i,\dots,x_{i+k-1}]}{x_{i+k}-x_i}")
    st.markdown(
        "Les dates sont normalisées sur [-1, 1] pour la stabilité numérique. Les nœuds de Tchebychev-Lobatto "
        "`x_k = cos(kπ/n)` minimisent l'erreur d'interpolation et évitent le phénomène de Runge."
    )
    st.markdown("**Newton-Raphson** (raffinement des zéros de P'' et P')")
    st.latex(r"x_{n+1}=x_n-\frac{f(x_n)}{f'(x_n)}")
    st.markdown(
        "**Dérivées sur les données.** Filtre de Savitzky-Golay (polynôme local de degré 3) : il dérive les données bruitées "
        "sans amplifier le bruit. Un point d'inflexion est un changement de signe de f''; un extremum, un changement de signe de f'.\n\n"
        "**Lecture de l'état.** f' > 0 : hausse; f' < 0 : baisse; f'' > 0 : convexe (accélération vers le haut); "
        "f'' < 0 : concave (accélération vers le bas).\n\n"
        "**Limites.** Un polynôme de Newton de haut degré ne doit pas servir à prévoir (extrapolation instable). "
        "Cette application est pédagogique et ne constitue pas un conseil financier."
    )

metal, n_nodes, node_type, win = sidebar()
df, sources = data.load_prices(10)

if df.empty:
    st.error("Impossible de récupérer les prix via les API. Vérifiez la connexion Internet ou importez un CSV.")
    up = st.file_uploader("CSV de secours (colonnes : Date, Or, Argent)", type="csv")
    if up is None:
        st.stop()
    df = pd.read_csv(up, parse_dates=["Date"], index_col="Date").sort_index().dropna()
    sources = {"Or": "CSV importé", "Argent": "CSV importé"}

df1 = data.last_year(df)
ret10, ret1 = stats.log_returns(df), stats.log_returns(df1)
nw = numerics.build_newton(df1[metal], n_nodes, node_type)

header(df, df1, sources)

tabs = st.tabs(
    [
        "Vue 10 ans",
        "Année en cours",
        "Matrices & statistiques",
        "Interpolation de Newton",
        "Dérivées & inflexions",
        "Méthodologie",
    ]
)
with tabs[0]:
    tab_overview(df, ret10)
with tabs[1]:
    tab_year(df, df1, ret1)
with tabs[2]:
    tab_matrices(ret10, ret1)
with tabs[3]:
    tab_newton(nw, metal, node_type, n_nodes)
with tabs[4]:
    tab_derivatives(df, df1, nw, metal, win)
with tabs[5]:
    tab_method()
#display_docx("rapport.docx")
