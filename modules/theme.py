import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

YELLOW = "#F0B90B"
YELLOW_HOVER = "#FCD535"
GREEN = "#0ECB81"
RED = "#F6465D"
BLUE = "#5B8DEF"
VIOLET = "#A66CFF"
BG = "#0B0E11"
PANEL = "#181A20"
CARD = "#1E2329"
BORDER = "#2B3139"
TEXT = "#EAECEF"
MUTED = "#848E9C"

METAL_COLORS = {"Or": YELLOW, "Argent": "#B7BDC6"}
DIVERGING = [[0, RED], [0.5, CARD], [1, GREEN]]
SEQUENTIAL = [[0, PANEL], [1, YELLOW]]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', 'Segoe UI', Arial, sans-serif; }
.stApp { background: __BG__; color: __TEXT__; }
[data-testid="stHeader"] { background: __BG__; }
[data-testid="stSidebar"] { background: __PANEL__; border-right: 1px solid __BORDER__; color: #FFFFFF; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] span, [data-testid="stSidebar"] li,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-testid="stSliderThumbValue"],
[data-testid="stSidebar"] [data-testid="stTickBarMin"],
[data-testid="stSidebar"] [data-testid="stTickBarMax"] { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stButton > button, [data-testid="stSidebar"] .stButton > button p { color: __PANEL__ !important; }
.block-container { padding-top: 4.5rem; max-width: 1500px; }
[data-testid="stSidebarUserContent"] { padding-top: 2.5rem; }
h1, h2, h3, h4 { color: __TEXT__; font-weight: 600; letter-spacing: 0.1px; }
.brand { display: flex; align-items: center; gap: 12px; margin: 4px 0 2px 0; }
.brand .logo { color: __BG__; background: __YELLOW__; width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; }
.brand .name { font-size: 1.65rem; font-weight: 600; color: __TEXT__; }
.brand .name b { color: __YELLOW__; font-weight: 600; }
.sub { color: __MUTED__; font-size: 0.9rem; margin-bottom: 14px; }
.ticker { display: flex; flex-wrap: wrap; gap: 32px; padding: 12px 18px; background: __PANEL__;
  border: 1px solid __BORDER__; border-radius: 8px; margin-bottom: 16px; }
.tk { display: flex; align-items: baseline; gap: 10px; }
.tk-name { color: __MUTED__; font-size: 0.85rem; font-weight: 500; }
.tk-price { font-size: 1.05rem; font-weight: 600; font-variant-numeric: tabular-nums; color: __TEXT__; }
.tk-chg { font-size: 0.85rem; font-weight: 500; font-variant-numeric: tabular-nums; }
.up { color: __GREEN__ !important; }
.down { color: __RED__ !important; }
[data-testid="stMetric"] { background: __CARD__; border: 1px solid __BORDER__; border-radius: 8px; padding: 14px 16px; }
[data-testid="stMetricLabel"] p { color: __MUTED__; font-size: 0.8rem; }
[data-testid="stMetricValue"] { color: __TEXT__; font-weight: 600; font-variant-numeric: tabular-nums; }
button[data-baseweb="tab"] { color: __MUTED__; font-weight: 500; }
button[data-baseweb="tab"][aria-selected="true"] { color: __YELLOW__; }
div[data-baseweb="tab-highlight"] { background-color: __YELLOW__; }
div[data-baseweb="tab-border"] { background-color: __BORDER__; }
.stButton > button { background: __YELLOW__; color: __PANEL__; border: 0; border-radius: 6px; font-weight: 600; }
.stButton > button:hover { background: __YELLOW_HOVER__; color: __PANEL__; }
[data-testid="stDataFrame"] { border: 1px solid __BORDER__; border-radius: 8px; overflow: hidden; }
[data-testid="stAlert"] { background: __CARD__; border: 1px solid __BORDER__; border-radius: 8px; }
[data-testid="stPlotlyChart"] { border: 1px solid __BORDER__; border-radius: 8px; overflow: hidden; background: __PANEL__; }
hr { border-color: __BORDER__; }
"""


def inject_css():
    css = CSS
    tokens = {
        "__BG__": BG,
        "__PANEL__": PANEL,
        "__CARD__": CARD,
        "__BORDER__": BORDER,
        "__TEXT__": TEXT,
        "__MUTED__": MUTED,
        "__YELLOW__": YELLOW,
        "__YELLOW_HOVER__": YELLOW_HOVER,
        "__GREEN__": GREEN,
        "__RED__": RED,
    }
    for key, value in tokens.items():
        css = css.replace(key, value)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def brand_html():
    return (
        '<div class="brand"><div class="logo">◆</div>'
        '<div class="name">Observatoire <b>Or</b> &amp; <b>Argent</b></div></div>'
        '<div class="sub">Marchés des métaux précieux : 10 ans d\'historique, analyse de l\'année en cours, '
        "interpolation de Newton, dérivées et points d'inflexion.</div>"
    )


def ticker_html(items):
    cells = []
    for name, value, pct in items:
        if pct is None:
            cells.append(f'<div class="tk"><span class="tk-name">{name}</span><span class="tk-price">{value}</span></div>')
            continue
        cls = "up" if pct >= 0 else "down"
        sign = "+" if pct >= 0 else ""
        cells.append(
            f'<div class="tk"><span class="tk-name">{name}</span>'
            f'<span class="tk-price {cls}">{value}</span>'
            f'<span class="tk-chg {cls}">{sign}{pct:.2f} %</span></div>'
        )
    return '<div class="ticker">' + "".join(cells) + "</div>"


def register_plotly_theme():
    axis = dict(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER, tickfont=dict(color=MUTED))
    pio.templates["binance"] = go.layout.Template(
        layout=dict(
            paper_bgcolor=PANEL,
            plot_bgcolor=PANEL,
            font=dict(family="IBM Plex Sans, Segoe UI, Arial, sans-serif", color=TEXT, size=12),
            colorway=[YELLOW, "#B7BDC6", GREEN, RED, BLUE, VIOLET],
            xaxis=axis,
            yaxis=axis,
            title=dict(font=dict(size=15, color=TEXT), x=0.01),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED)),
            margin=dict(l=55, r=20, t=55, b=35),
            hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font=dict(color=TEXT)),
            hovermode="x unified",
        )
    )
    pio.templates.default = "binance"


def line_fig(series, title, color, ytitle="USD / once troy", height=380):
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines", line=dict(color=color, width=2), name=title))
    fig.update_layout(title=title, yaxis_title=ytitle, height=height, showlegend=False)
    return fig


def heat(matrix, title, kind="cov", height=340, decimals=".4f"):
    if kind == "corr":
        fig = px.imshow(matrix, text_auto=decimals, color_continuous_scale=DIVERGING, zmin=-1, zmax=1, aspect="auto", title=title)
    elif kind == "diverging":
        fig = px.imshow(matrix, text_auto=decimals, color_continuous_scale=DIVERGING, color_continuous_midpoint=0, aspect="auto", title=title)
    else:
        fig = px.imshow(matrix, text_auto=decimals, color_continuous_scale=SEQUENTIAL, aspect="auto", title=title)
    fig.update_layout(height=height, coloraxis_colorbar=dict(tickfont=dict(color=MUTED)))
    return fig