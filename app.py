from __future__ import annotations

from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.lifecycle_analysis import (
    DEFAULT_DATA_PATH,
    attribute_summary,
    monthly_rotation,
    prepare_data,
    stage_distribution,
)


STAGE_COLORS = {
    "New Entry": "#1DB954",
    "Growth Phase": "#2D9CDB",
    "Peak Phase": "#F2C94C",
    "Mature Phase": "#BB86FC",
    "Decline Phase": "#EB5757",
}

FLOW_COLORS = {"entries": "#1DB954", "exits": "#EB5757"}
RELEASE_COLORS = {"Single": "#1DB954", "Album": "#BB86FC"}
EXPLICIT_COLORS = {"Explicit": "#EB5757", "Clean": "#1DB954"}


st.set_page_config(
    page_title="Spain50 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

        html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
            font-family: 'Outfit', sans-serif;
        }

        /* Target custom dashboard elements specifically to apply Outfit font cleanly */
        .stApp,
        .metric-card, .metric-value, .metric-label, .metric-note,
        .sidebar-brand, .sidebar-brand-title, .sidebar-brand-sub, .sidebar-section-label,
        .hero-title, .hero-copy, .hero-topline,
        .section-title,
        .album-title, .album-artist, .album-rank,
        .track-focus-title, .track-focus-meta,
        .stButton button, .stButton button p,
        [data-testid="stTabs"] button,
        [data-testid="stDataFrame"] *, [data-testid="stTable"] *,
        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-baseweb="select"] * {
            font-family: 'Outfit', sans-serif !important;
        }

        /* Premium custom scrollbars */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #050505;
        }
        ::-webkit-scrollbar-thumb {
            background: #242424;
            border-radius: 999px;
            transition: background 0.25s ease;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #1DB954;
        }

        :root {
            --bg: #050505;
            --panel: rgba(18, 18, 18, 0.6);
            --panel-2: rgba(24, 24, 24, 0.75);
            --panel-3: rgba(36, 36, 36, 0.85);
            --border: rgba(255,255,255,.06);
            --text: #f5f5f5;
            --muted: #b3b3b3;
            --accent: #1DB954;
            --blue: #2D9CDB;
            --gold: #f2c94c;
            --green: #1DB954;
            --red: #EB5757;
        }

        .stApp {
            background:
                radial-gradient(circle at 18% 0%, rgba(29,185,84,.22), transparent 28rem),
                linear-gradient(180deg, #050505 0%, #0a0a0a 46%, #050505 100%);
            color: var(--text);
        }

        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes softPulse {
            0%, 100% { box-shadow: 0 0 0 rgba(29,185,84,0); }
            50% { box-shadow: 0 0 26px rgba(29,185,84,.18); }
        }

        @keyframes albumFloat {
            from { opacity: 0; transform: translateY(16px) scale(.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1240px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }

        [data-testid="stHeader"] {
            background: rgba(5,5,5,.82);
            backdrop-filter: blur(10px);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #000 0%, #101010 100%);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
            letter-spacing: 0;
        }

        .sidebar-brand {
            background: linear-gradient(135deg, rgba(29,185,84,.28), rgba(18,18,18,.98));
            border: 1px solid rgba(29,185,84,.28);
            border-radius: 8px;
            padding: .9rem;
            margin: .25rem 0 1rem;
        }

        .sidebar-brand-title {
            color: #fff;
            font-size: 1.05rem;
            font-weight: 900;
            line-height: 1.1;
        }

        .sidebar-brand-sub {
            color: #c7f8d6;
            font-size: .78rem;
            margin-top: .35rem;
            line-height: 1.35;
        }

        .sidebar-credit {
            margin-top: auto;
            padding: 1.2rem 1rem 0.8rem;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,.07);
            font-size: 1rem;
            color: var(--muted);
            letter-spacing: .03em;
        }
        .sidebar-credit a {
            color: var(--accent);
            font-weight: 700;
            text-decoration: none;
            transition: opacity .2s;
        }
        .sidebar-credit a:hover { opacity: .75; }

        .page-footer {
            margin-top: 3rem;
            padding: 1.5rem 0;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,.07);
            font-size: 1.05rem;
            color: var(--muted);
            letter-spacing: .03em;
        }
        .page-footer a {
            color: var(--accent);
            font-weight: 700;
            text-decoration: none;
            transition: opacity .2s;
        }
        .page-footer a:hover { opacity: .75; }

        .sidebar-section-label {
            color: var(--muted);
            font-size: .72rem;
            font-weight: 900;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin: 1.05rem 0 .45rem;
        }

        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] .stDateInput input,
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: #121212;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 8px;
            transition: border-color 0.25s ease;
        }

        [data-testid="stSidebar"] .stTextInput input:focus,
        [data-testid="stSidebar"] .stDateInput input:focus,
        [data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
            border-color: rgba(29, 185, 84, 0.5) !important;
        }

        /* Vertically center "Press Enter to apply" hint inside date input */
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-testid="stDateInput"] [data-baseweb="base-input"] {
            display: flex !important;
            align-items: center !important;
        }
        [data-testid="stDateInput"] input + div,
        [data-testid="stDateInput"] [data-testid="InputInstructions"] {
            display: flex !important;
            align-items: center !important;
            align-self: center !important;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            position: relative !important;
        }

        [data-testid="stFileUploader"] section {
            background: #121212;
            border: 1px dashed rgba(255,255,255,.20);
            border-radius: 8px;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            padding: 1.5rem 1rem !important;
        }

        [data-testid="stFileUploader"] section > div {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            gap: 8px !important;
        }

        [data-testid="stFileUploader"] section button {
            margin: 10px auto 0 !important;
            display: block !important;
        }

        [data-testid="stSidebar"] [data-baseweb="tag"] {
            background-color: var(--accent) !important;
            color: #041207 !important;
            border-radius: 999px !important;
            font-weight: 800 !important;
            transition: transform 0.15s ease !important;
        }
        [data-testid="stSidebar"] [data-baseweb="tag"]:hover {
            transform: scale(1.05) !important;
        }

        .hero-shell {
            border: 1px solid var(--border);
            background:
                linear-gradient(135deg, rgba(29,185,84,.22), rgba(18,18,18,.98) 42%, rgba(18,18,18,.98)),
                #121212;
            border-radius: 8px;
            padding: 1rem 1.15rem 1.05rem;
            margin-bottom: .9rem;
            box-shadow: 0 22px 60px rgba(0,0,0,.34);
            animation: fadeUp .55s ease both;
        }

        .hero-topline {
            color: var(--muted);
            font-size: .78rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: .45rem;
        }

        .hero-title {
            color: var(--text);
            font-size: clamp(1.75rem, 3.2vw, 2.9rem);
            font-weight: 800;
            line-height: 1.04;
            margin: 0;
            letter-spacing: 0;
        }

        /* Hide Streamlit's auto-injected anchor link icon on headings */
        a.anchor-link,
        .anchor-link,
        h1 a, h2 a, h3 a, h4 a,
        .hero-title a,
        [data-testid="stMarkdownContainer"] h1 a,
        [data-testid="stMarkdownContainer"] h2 a,
        [data-testid="stMarkdownContainer"] h3 a,
        [data-testid="stHeadingWithActionElements"] button,
        [data-testid="stHeadingWithActionElements"] a {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }

        .hero-copy {
            color: var(--muted);
            max-width: 760px;
            font-size: 1rem;
            line-height: 1.55;
            margin: .7rem 0 0;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: .8rem;
            margin: .85rem 0 .85rem;
        }

        .metric-card {
            background: var(--panel) !important;
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: .95rem .95rem .9rem;
            min-height: 98px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            animation: fadeUp .45s ease both;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        .metric-card:hover {
            background: var(--panel-2) !important;
            border-color: rgba(29, 185, 84, 0.35);
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 30px rgba(29, 185, 84, 0.15);
        }

        .metric-label {
            color: var(--muted);
            font-size: .78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .06em;
            white-space: nowrap;
        }

        .metric-value {
            color: var(--text);
            font-size: 1.9rem;
            font-weight: 800;
            line-height: 1.1;
            margin-top: .55rem;
            letter-spacing: 0;
        }

        .metric-note {
            color: var(--muted);
            font-size: .78rem;
            margin-top: .35rem;
        }

        .maturity-metric-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1.2rem;
            margin: .85rem 0 1.5rem;
            width: 100%;
        }

        .maturity-metric-card {
            background: var(--panel) !important;
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem;
            min-height: 120px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            animation: fadeUp .45s ease both;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .maturity-metric-card:hover {
            background: var(--panel-2) !important;
            border-color: rgba(29, 185, 84, 0.45);
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 35px rgba(29, 185, 84, 0.2);
        }

        .maturity-metric-label {
            color: var(--muted);
            font-size: .85rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: .06em;
            white-space: nowrap;
        }

        .maturity-metric-value {
            color: var(--accent);
            font-size: 2.8rem;
            font-weight: 900;
            line-height: 1.1;
            margin-top: .45rem;
            letter-spacing: -0.02em;
        }

        .maturity-metric-note {
            color: var(--muted);
            font-size: .85rem;
            margin-top: .35rem;
        }

        .quality-note {
            border: 1px solid rgba(29,185,84,.28);
            background: rgba(29,185,84,.10);
            color: #c7f8d6;
            border-radius: 8px;
            padding: .85rem 1rem;
            margin: .75rem 0 1rem;
            font-weight: 650;
            animation: fadeUp .55s ease both;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--text);
            margin: .35rem 0 .65rem;
            letter-spacing: 0;
        }

        .album-rail {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: .8rem;
            margin: .75rem 0 1rem;
        }

        .album-card {
            background: var(--panel);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: .65rem;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            min-width: 0;
            animation: albumFloat .5s ease both;
        }

        .album-card:hover {
            background: var(--panel-3);
            border-color: rgba(29, 185, 84, 0.4);
            transform: scale(1.05) translateY(-5px);
            box-shadow: 0 15px 30px rgba(29, 185, 84, 0.2);
        }

        .album-card img {
            width: 100%;
            aspect-ratio: 1 / 1;
            object-fit: cover;
            border-radius: 6px;
            display: block;
            box-shadow: 0 12px 28px rgba(0,0,0,.38);
        }

        .album-rank {
            color: var(--accent);
            font-size: .72rem;
            font-weight: 900;
            margin-top: .55rem;
            text-transform: uppercase;
        }

        .album-title {
            color: var(--text);
            font-size: .88rem;
            font-weight: 800;
            margin-top: .18rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .album-artist {
            color: var(--muted);
            font-size: .78rem;
            margin-top: .1rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .track-focus {
            display: grid;
            grid-template-columns: 112px minmax(0, 1fr);
            gap: 1rem;
            align-items: center;
            background: #181818;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 8px;
            padding: .8rem;
            margin: .4rem 0 .9rem;
            animation: fadeUp .45s ease both;
        }

        .track-focus img {
            width: 112px;
            height: 112px;
            object-fit: cover;
            border-radius: 6px;
            box-shadow: 0 16px 32px rgba(0,0,0,.45);
        }

        .track-focus-title {
            color: #fff;
            font-size: 1.35rem;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: .35rem;
        }

        .track-focus-meta {
            color: var(--muted);
            font-size: .92rem;
            line-height: 1.5;
        }

        [data-testid="stTabs"] button {
            color: #d9d7d1;
            font-weight: 700;
            letter-spacing: 0;
            flex-grow: 1 !important;
            width: 100% !important;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #ffffff;
        }

        [data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
            background-color: var(--accent);
        }

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }

        div[data-testid="stAltairChart"] {
            background: var(--panel);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: .75rem;
            animation: fadeUp .5s ease both;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        }

        div[data-testid="stTextInput"] input {
            background: #181818;
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 8px;
            color: #fff;
            min-height: 46px;
            padding-left: 1.15rem;
            padding-right: 1.15rem;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: rgba(29,185,84,.75);
            box-shadow: 0 0 0 1px rgba(29,185,84,.35);
        }

        .stButton button {
            background: var(--accent);
            border: 0;
            border-radius: 999px;
            min-height: 42px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .stButton button p {
            color: #041207 !important;
            font-weight: 800 !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
        }

        .stButton button:hover {
            background: #25d366 !important;
            border: 0;
        }

        .stButton button:hover p {
            color: #041207 !important;
        }

        .search-shell {
            animation: fadeUp .4s ease both;
            margin-bottom: .75rem;
            display: grid;
            grid-template-columns: 1fr auto;
            gap: .75rem;
            align-items: center;
        }

        /* Match the columns container adjacent to or containing the search shell */
        div[data-testid="element-container"]:has(.search-shell) + div[data-testid="stHorizontalBlock"] .stTextInput,
        div[data-testid="element-container"]:has(.search-shell) + div[data-testid="stHorizontalBlock"] .stButton,
        div[data-testid="element-container"]:has(.search-shell) + div[data-testid="element-container"] .stTextInput,
        div[data-testid="element-container"]:has(.search-shell) + div[data-testid="element-container"] .stButton,
        .search-shell .stTextInput,
        .search-shell .stButton {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            min-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        div[data-testid="element-container"]:has(.search-shell) + div[data-testid="stHorizontalBlock"] .stTextInput input,
        div[data-testid="element-container"]:has(.search-shell) + div[data-testid="element-container"] .stTextInput input,
        .search-shell .stTextInput input {
            min-height: 44px !important;
            height: 44px !important;
            padding: 0 1rem !important;
        }

        /* Match the search button inside the main body container */
        [data-testid="stMain"] .stButton button {
            width: 100% !important;
            min-height: 44px !important;
            height: 44px !important;
            line-height: 44px !important;
            background: #1DB954 !important;
            border-radius: 999px !important;
            border: 1px solid rgba(255,255,255,.08) !important;
            box-shadow: 0 2px 6px rgba(0,0,0,.18) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 1.2rem !important;
        }

        /* Styling specifically for the search button text element */
        div[data-testid="element-container"]:has(.search-button) + div[data-testid="element-container"] .stButton button p,
        .search-button .stButton button p {
            color: #041207 !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            letter-spacing: .02em !important;
            text-transform: none !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
            display: inline-block !important;
        }

        [data-testid="stMain"] .stButton button p {
            font-size: 1.1rem !important;
            font-weight: 800 !important;
            color: #041207 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        div[data-testid="element-container"]:has(.search-button) + div[data-testid="element-container"] .stButton button:hover,
        .search-button .stButton button:hover {
            background: #25d366 !important;
        }

        div[data-testid="element-container"]:has(.search-button) + div[data-testid="element-container"] .stButton button:hover p,
        .search-button .stButton button:hover p {
            background: transparent !important;
            color: #041207 !important;
        }

        .stAlert {
            border-radius: 8px;
        }

        @media (max-width: 1100px) {
            .metric-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
            .album-rail { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }

        @media (max-width: 720px) {
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .album-rail { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .track-focus { grid-template-columns: 76px minmax(0, 1fr); }
            .track-focus img { width: 76px; height: 76px; }
            .hero-shell { padding: 1rem; }
            .metric-value { font-size: 1.55rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_prepared_data(source_kind: str, source_value):
    if source_kind == "upload":
        return prepare_data(source_value)
    return prepare_data(Path(source_value))


def fmt_num(value, suffix: str = "", digits: int = 1) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:.{digits}f}{suffix}"


def chart_style(chart: alt.Chart) -> alt.Chart:
    return chart.configure_view(strokeWidth=0).configure_axis(
        labelColor="#b3b3b3",
        titleColor="#ffffff",
        gridColor="rgba(255,255,255,.06)",
        domainColor="rgba(255,255,255,.12)",
        tickColor="rgba(255,255,255,.12)",
        gridDash=[3, 4],
        labelFontSize=12,
        titleFontSize=12,
    ).configure_legend(
        labelColor="#ffffff",
        titleColor="#b3b3b3",
        labelFontSize=12,
        titleFontSize=12,
        orient="right",
    ).configure_title(
        color="#ffffff",
        fontSize=15,
        fontWeight=700,
    )


def color_scale(mapping: dict[str, str]) -> alt.Scale:
    return alt.Scale(domain=list(mapping.keys()), range=list(mapping.values()))


def commit_search() -> None:
    """Copy the transient input into the persistent search state."""
    st.session_state["catalog_search"] = st.session_state.get("catalog_search_input", "")


def clear_search() -> None:
    """Clear both the input widget and the persisted search state."""
    st.session_state["catalog_search_input"] = ""
    st.session_state["catalog_search"] = ""


def render_metric_grid(metrics: list[tuple[str, str, str]]) -> None:
    import re as _re

    def _extract(val: str):
        """Return (numeric_float, suffix) from a formatted value string like '48.2', '3.5%', '575'."""
        m = _re.match(r"^([\d,]+\.?\d*)(%?)$", val.strip())
        if m:
            return float(m.group(1).replace(",", "")), m.group(2)
        return None, ""

    card_id_base = "kpi"
    cards_html = []
    js_targets = []

    for i, (label, value, note) in enumerate(metrics):
        cid = f"{card_id_base}_{i}"
        num, suffix = _extract(value)
        if num is not None:
            cards_html.append(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value" id="{cid}" data-target="{num}" data-suffix="{suffix}">0{suffix}</div>'
                f'<div class="metric-note">{note}</div>'
                f'</div>'
            )
            js_targets.append(cid)
        else:
            cards_html.append(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f'<div class="metric-note">{note}</div>'
                f'</div>'
            )

    ids_json = "[" + ",".join(f'"{c}"' for c in js_targets) + "]"

    anim_js = f"""
    <script>
    (function() {{
        var ids = {ids_json};
        var duration = 1400;
        var startTime = null;

        function easeOut(t) {{ return 1 - Math.pow(1 - t, 3); }}

        function formatNum(val, isFloat) {{
            if (isFloat) return val.toFixed(1);
            return Math.round(val).toLocaleString();
        }}

        function animate(timestamp) {{
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = easeOut(progress);

            ids.forEach(function(id) {{
                var el = document.getElementById(id);
                if (!el) return;
                var target = parseFloat(el.dataset.target);
                var suffix = el.dataset.suffix || "";
                var isFloat = (el.dataset.target.indexOf(".") !== -1);
                el.textContent = formatNum(target * eased, isFloat) + suffix;
            }});

            if (progress < 1) requestAnimationFrame(animate);
        }}

        // Wait for DOM to be ready then kick off animation
        function start() {{
            requestAnimationFrame(animate);
        }}
        if (document.readyState === "loading") {{
            document.addEventListener("DOMContentLoaded", start);
        }} else {{
            start();
        }}
    }})();
    </script>
    """

    st.markdown(
        f'<div class="metric-grid">{"".join(cards_html)}</div>{anim_js}',
        unsafe_allow_html=True,
    )


def latest_unique_artwork(rows: pd.DataFrame, limit: int = 6) -> pd.DataFrame:
    if rows.empty:
        return rows
    latest_date = rows["date_dt"].max()
    return (
        rows[rows["date_dt"].eq(latest_date)]
        .sort_values("position")
        .drop_duplicates("album_cover_url")
        .head(limit)
    )


def render_album_rail(rows: pd.DataFrame, title: str = "Latest playlist covers") -> None:
    if rows.empty:
        return
    cards = []
    for _, row in rows.iterrows():
        cards.append(
            "".join(
                [
                    '<div class="album-card">',
                    f'<img src="{escape(str(row["album_cover_url"]))}" alt="{escape(str(row["song"]))} album cover">',
                    f'<div class="album-rank">#{int(row["position"])}</div>',
                    f'<div class="album-title">{escape(str(row["song"]))}</div>',
                    f'<div class="album-artist">{escape(str(row["artist"]))}</div>',
                    "</div>",
                ]
            )
        )
    st.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="album-rail">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_track_focus(row: pd.Series) -> None:
    explicit = "Explicit" if bool(row["is_explicit"]) else "Clean"
    st.markdown(
        "".join(
            [
                '<div class="track-focus">',
                f'<img src="{escape(str(row["album_cover_url"]))}" alt="{escape(str(row["song"]))} album cover">',
                "<div>",
                f'<div class="track-focus-title">{escape(str(row["song"]))}</div>',
                f'<div class="track-focus-meta">{escape(str(row["artist"]))}<br>',
                f'Peak #{int(row["peak_position"])} | {int(row["observed_days"])} playlist days | ',
                f'{escape(str(row["release_form"]))} | {explicit}</div>',
                "</div></div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def date_filter(df: pd.DataFrame, date_range) -> pd.DataFrame:
    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    return df[df["date_dt"].between(start, end)]


def line_rank_chart(song_rows: pd.DataFrame) -> alt.Chart:
    base = alt.Chart(song_rows).encode(
        x=alt.X("date_dt:T", title="Date", axis=alt.Axis(format="%b %d")),
        y=alt.Y(
            "position:Q",
            title="Playlist position (1 is best)",
            scale=alt.Scale(reverse=True),
        ),
        color=alt.Color("stage:N", title="Lifecycle stage", scale=color_scale(STAGE_COLORS)),
        tooltip=[
            alt.Tooltip("date_dt:T", title="Date"),
            alt.Tooltip("position:Q", title="Position"),
            alt.Tooltip("popularity:Q", title="Popularity"),
            alt.Tooltip("stage:N", title="Stage"),
        ],
    )
    chart = (
        base.mark_line(interpolate="monotone", strokeWidth=3)
        + base.mark_circle(size=72, opacity=0.9, stroke="#050505", strokeWidth=1.5)
    ).properties(height=390)
    return chart_style(chart)


def bar_chart(df: pd.DataFrame, x: str, y: str, color: str | None = None, title: str | None = None):
    chart_df = df.sort_values(y, ascending=False).copy()
    sort_order = chart_df[x].astype(str).tolist()
    scale = None
    if color == "stage":
        scale = color_scale(STAGE_COLORS)
    if color == "explicit_label":
        scale = color_scale(EXPLICIT_COLORS)
    if color == "release_form":
        scale = color_scale(RELEASE_COLORS)

    if color and scale:
        color_encoding = alt.Color(f"{color}:N", legend=None, scale=scale)
    elif color:
        color_encoding = alt.Color(f"{color}:N", legend=None)
    else:
        color_encoding = alt.value("#1DB954")

    text_format = ",.0f" if y in {"observations", "songs"} else ".1f"
    base = alt.Chart(chart_df).encode(
        y=alt.Y(f"{x}:N", sort=sort_order, title=None, axis=alt.Axis(labelLimit=190)),
        x=alt.X(f"{y}:Q", title=y.replace("_", " ").title()),
        tooltip=list(df.columns),
    )
    bars = base.mark_bar(cornerRadiusEnd=8, height=24).encode(color=color_encoding)
    labels = base.mark_text(
        align="left",
        baseline="middle",
        dx=8,
        color="#f5f5f5",
        fontSize=12,
        fontWeight=700,
    ).encode(text=alt.Text(f"{y}:Q", format=text_format))
    chart = (bars + labels).properties(height=max(230, min(360, 48 * len(chart_df))))
    if title:
        chart = chart.properties(title=title)
    return chart_style(chart)


def main() -> None:
    inject_global_styles()

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-title">Spain50 Analytics</div>
                <div class="sidebar-brand-sub">Daily Top 50 Playlist Intelligence</div>
            </div>
            <div class="sidebar-section-label">Source</div>
            """,
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload playlist CSV or Excel", type=["csv", "xlsx", "xls"])

    try:
        if uploaded is not None:
            prepared = load_prepared_data("upload", uploaded)
        else:
            prepared = load_prepared_data("path", DEFAULT_DATA_PATH)
    except Exception as exc:
        st.error(f"Could not load data: {exc}")
        st.stop()

    daily = prepared.daily
    lifecycle = prepared.lifecycle
    stage_daily = prepared.stage_daily
    churn = prepared.churn_daily
    validation = prepared.validation
    kpis = prepared.kpis

    min_date = daily["date_dt"].min().date()
    max_date = daily["date_dt"].max().date()

    with st.sidebar:
        st.markdown('<div class="sidebar-section-label">Filters</div>', unsafe_allow_html=True)
        date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        if not isinstance(date_range, tuple) or len(date_range) != 2:
            st.info("Select a start and end date.")
            st.stop()

        stages = sorted(stage_daily["stage"].unique())
        selected_stages = st.multiselect("Lifecycle stages", stages, default=stages)
        explicit_options = ["Explicit", "Clean"]
        selected_explicit = st.multiselect("Content maturity", explicit_options, default=explicit_options)
        album_options = sorted(lifecycle["release_form"].unique())
        selected_album = st.multiselect("Release form", album_options, default=album_options)
        st.markdown(
            '<div class="sidebar-credit">Made with ❤️ by <a href="https://github.com/Sunny210405" target="_blank">SUNNY</a></div>',
            unsafe_allow_html=True,
        )

    if "catalog_search" not in st.session_state:
        st.session_state["catalog_search"] = ""
    st.markdown('<div class="search-shell">', unsafe_allow_html=True)
    search_col, button_col = st.columns([13, 3], vertical_alignment="center")
    with search_col:
        st.text_input(
            "Search by song or artist",
            key="catalog_search_input",
            placeholder="Type a song or artist then click Search...",
            label_visibility="collapsed",
            on_change=commit_search,
        )
    with button_col:
        if st.button("Search", key="catalog_search_button", use_container_width=True):
            commit_search()
    st.markdown("</div>", unsafe_allow_html=True)

    search = st.session_state["catalog_search"]

    filtered_stage = date_filter(stage_daily, date_range)
    filtered_stage = filtered_stage[
        filtered_stage["stage"].isin(selected_stages)
        & filtered_stage["explicit_label"].isin(selected_explicit)
        & filtered_stage["release_form"].isin(selected_album)
    ]
    if search.strip():
        q = search.strip().lower()
        filtered_stage = filtered_stage[
            filtered_stage["song"].str.lower().str.contains(q, regex=False)
            | filtered_stage["artist"].str.lower().str.contains(q, regex=False)
        ]

    visible_keys = filtered_stage["song_key"].unique()
    filtered_lifecycle = lifecycle[lifecycle["song_key"].isin(visible_keys)].copy()
    filtered_churn = date_filter(churn, date_range)
    latest_artwork = latest_unique_artwork(filtered_stage, 6)

    st.markdown(
        """
        <section class="hero-shell">
            <div class="hero-topline">Spain50 Analytics • Daily Top 50 Playlist Intelligence</div>
            <h1 class="hero-title">Playlist Lifecycle Intelligence</h1>
            <p class="hero-copy">
                Track entries, exits, maturity, and retention with album artwork, content filters,
                and release-form diagnostics for Spain's daily Top 50.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    avg_days = filtered_lifecycle["observed_days"].mean() if len(filtered_lifecycle) else pd.NA
    peak_time = filtered_lifecycle["entry_to_peak_days"].mean() if len(filtered_lifecycle) else pd.NA
    churn_rate = filtered_churn["churn_rate"].dropna().mean() * 100
    stability = filtered_churn["retention_stability_index"].dropna().mean() * 100
    unique_songs = filtered_lifecycle["song_key"].nunique()
    playlist_days = filtered_stage["date_dt"].nunique()

    render_metric_grid(
        [
            ("Avg days", fmt_num(avg_days), "playlist survival"),
            ("Entry to peak", fmt_num(peak_time), "maturity speed"),
            ("Churn rate", fmt_num(churn_rate, "%"), "daily rotation"),
            ("Stability", fmt_num(stability, "%"), "day-to-day overlap"),
            ("Songs", f"{unique_songs:,}", "filtered catalog"),
            ("Days", f"{playlist_days:,}", "snapshots in range"),
        ]
    )

    render_album_rail(latest_artwork, "Latest filtered Top 50 covers")

    if kpis["validation_failed_days"] or kpis["missing_calendar_dates"]:
        st.markdown(
            f"""
            <div class="quality-note">
                Validation note: {kpis['validation_failed_days']} date(s) fail the raw 50-entry rule;
                {kpis['missing_calendar_dates']} calendar date(s) are absent from the observed range.
                Lifecycle calculations use a cleaned one-row-per-date-position table.
            </div>
            """,
            unsafe_allow_html=True,
        )

    tabs = st.tabs(
        [
            "Overview",
            "Song Timeline",
            "Entry Exit Flow",
            "Content Maturity",
            "Churn Analytics",
            "Song Explorer",
            "Validation",
        ]
    )

    with tabs[0]:
        left, right = st.columns([1, 1])
        with left:
            st.markdown('<div class="section-title">Lifecycle stage distribution</div>', unsafe_allow_html=True)
            dist = stage_distribution(filtered_stage) if len(filtered_stage) else pd.DataFrame()
            if len(dist):
                st.altair_chart(bar_chart(dist, "stage", "observations", "stage"), use_container_width=True)
            else:
                st.info("No rows match the selected filters.")
        with right:
            st.markdown('<div class="section-title">Top lifecycle performers</div>', unsafe_allow_html=True)
            table = filtered_lifecycle[
                [
                    "album_cover_url",
                    "song",
                    "artist",
                    "release_form",
                    "explicit_label",
                    "entry_date",
                    "exit_date",
                    "observed_days",
                    "peak_position",
                    "entry_to_peak_days",
                    "avg_popularity",
                ]
            ].head(15)
            if len(table):
                st.dataframe(
                    table,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "album_cover_url": st.column_config.ImageColumn("Cover", width="small"),
                        "entry_date": st.column_config.DateColumn("Entry"),
                        "exit_date": st.column_config.DateColumn("Exit"),
                        "avg_popularity": st.column_config.NumberColumn("Avg popularity", format="%.1f"),
                    },
                )

    with tabs[1]:
        if filtered_lifecycle.empty:
            st.info("No songs match the selected filters.")
        else:
            choices = (
                filtered_lifecycle.assign(label=lambda d: d["song"] + " - " + d["artist"])
                .sort_values(["observed_days", "peak_position"], ascending=[False, True])
                [["label", "song_key"]]
            )
            selected_label = st.selectbox("Song", choices["label"].tolist())
            selected_key = choices.loc[choices["label"].eq(selected_label), "song_key"].iloc[0]
            selected_meta = lifecycle[lifecycle["song_key"].eq(selected_key)].iloc[0]
            render_track_focus(selected_meta)
            song_rows = stage_daily[stage_daily["song_key"].eq(selected_key)].sort_values("date_dt")
            st.altair_chart(line_rank_chart(song_rows), use_container_width=True)
            st.dataframe(
                song_rows[
                    [
                        "date_dt",
                        "position",
                        "popularity",
                        "stage",
                        "days_since_entry",
                        "rank_delta",
                        "release_form",
                        "explicit_label",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[2]:
        st.markdown('<div class="section-title">Daily entry and exit flow</div>', unsafe_allow_html=True)
        flow = filtered_churn.copy()
        flow_long = flow.melt(
            id_vars=["date_dt"],
            value_vars=["entries", "exits"],
            var_name="flow",
            value_name="songs",
        )
        flow_chart = (
            alt.Chart(flow_long)
            .mark_area(interpolate="monotone", opacity=0.18)
            .encode(
                x=alt.X("date_dt:T", title="Date", axis=alt.Axis(format="%b %d")),
                y=alt.Y("songs:Q", title="Songs"),
                color=alt.Color("flow:N", title="Flow", scale=color_scale(FLOW_COLORS)),
                tooltip=["date_dt:T", "flow:N", "songs:Q"],
            )
            + alt.Chart(flow_long)
            .mark_line(interpolate="monotone", strokeWidth=2.8)
            .encode(
                x=alt.X("date_dt:T", title="Date", axis=alt.Axis(format="%b %d")),
                y=alt.Y("songs:Q", title="Songs"),
                color=alt.Color("flow:N", title="Flow", scale=color_scale(FLOW_COLORS)),
                tooltip=["date_dt:T", "flow:N", "songs:Q"],
            )
            + alt.Chart(flow_long)
            .mark_circle(size=32, opacity=0.82, stroke="#050505", strokeWidth=1)
            .encode(
                x=alt.X("date_dt:T", title="Date", axis=alt.Axis(format="%b %d")),
                y=alt.Y("songs:Q", title="Songs"),
                color=alt.Color("flow:N", title="Flow", scale=color_scale(FLOW_COLORS)),
                tooltip=["date_dt:T", "flow:N", "songs:Q"],
            )
        )
        st.altair_chart(chart_style(flow_chart.properties(height=360)), use_container_width=True)

    with tabs[3]:
        # Dynamic explicit lifecycle score and release form longevity ratio calculations
        explicit_gp = filtered_lifecycle.groupby("explicit_label")["observed_days"].mean() if len(filtered_lifecycle) else pd.Series()
        if "Explicit" in explicit_gp and "Clean" in explicit_gp and explicit_gp["Clean"] != 0:
            dyn_explicit_score = explicit_gp["Explicit"] / explicit_gp["Clean"]
        else:
            dyn_explicit_score = pd.NA

        release_gp = filtered_lifecycle.groupby("release_form")["observed_days"].mean() if len(filtered_lifecycle) else pd.Series()
        if "Single" in release_gp and "Album" in release_gp and release_gp["Album"] != 0:
            dyn_single_album_ratio = release_gp["Single"] / release_gp["Album"]
        else:
            dyn_single_album_ratio = pd.NA

        score_str = f"{dyn_explicit_score:.2f}x" if not pd.isna(dyn_explicit_score) else "n/a"
        ratio_str = f"{dyn_single_album_ratio:.2f}x" if not pd.isna(dyn_single_album_ratio) else "n/a"

        st.markdown(
            f"""
            <div class="maturity-metric-grid">
                <div class="maturity-metric-card">
                    <div class="maturity-metric-label">Explicit Content Lifecycle Score</div>
                    <div class="maturity-metric-value">{score_str}</div>
                    <div class="maturity-metric-note">Explicit vs Clean average longevity ratio</div>
                </div>
                <div class="maturity-metric-card">
                    <div class="maturity-metric-label">Single vs Album Longevity Ratio</div>
                    <div class="maturity-metric-value">{ratio_str}</div>
                    <div class="maturity-metric-note">Singles vs Album tracks longevity ratio</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_a, col_b = st.columns(2)
        with col_a:
            explicit_summary = attribute_summary(filtered_lifecycle, "explicit_label") if len(filtered_lifecycle) else pd.DataFrame()
            st.markdown('<div class="section-title">Explicit vs clean</div>', unsafe_allow_html=True)
            st.dataframe(explicit_summary, use_container_width=True, hide_index=True)
            if len(explicit_summary):
                st.altair_chart(bar_chart(explicit_summary, "explicit_label", "avg_days", "explicit_label"), use_container_width=True)
        with col_b:
            release_summary = attribute_summary(filtered_lifecycle, "release_form") if len(filtered_lifecycle) else pd.DataFrame()
            st.markdown('<div class="section-title">Single vs album</div>', unsafe_allow_html=True)
            st.dataframe(release_summary, use_container_width=True, hide_index=True)
            if len(release_summary):
                st.altair_chart(bar_chart(release_summary, "release_form", "avg_days", "release_form"), use_container_width=True)

        st.markdown('<div class="section-title">Duration vs retention</div>', unsafe_allow_html=True)
        duration_chart = (
            alt.Chart(filtered_lifecycle)
            .mark_circle(opacity=0.78, stroke="#050505", strokeWidth=1.4)
            .encode(
                x=alt.X("duration_min:Q", title="Duration (minutes)"),
                y=alt.Y("observed_days:Q", title="Observed days on playlist"),
                color=alt.Color("release_form:N", title="Release form", scale=color_scale(RELEASE_COLORS)),
                size=alt.Size("avg_popularity:Q", title="Avg popularity", scale=alt.Scale(range=[45, 420])),
                tooltip=["song:N", "artist:N", "duration_min:Q", "observed_days:Q", "explicit_label:N"],
            )
            .properties(height=340)
        )
        st.altair_chart(chart_style(duration_chart), use_container_width=True)

    with tabs[4]:
        st.markdown('<div class="section-title">Monthly rotation profile</div>', unsafe_allow_html=True)
        monthly = monthly_rotation(filtered_churn)
        if len(monthly):
            monthly_long = monthly.melt(
                id_vars=["month"],
                value_vars=["avg_churn_rate", "avg_stability"],
                var_name="metric",
                value_name="value",
            )
            monthly_chart = (
                alt.Chart(monthly_long)
                .mark_area(interpolate="monotone", opacity=0.2)
                .encode(
                    x=alt.X("month:T", title="Month"),
                    y=alt.Y("value:Q", title="Rate"),
                    color=alt.Color("metric:N", title="Metric", scale=alt.Scale(range=["#1DB954", "#BB86FC"])),
                    tooltip=["month:T", "metric:N", alt.Tooltip("value:Q", format=".2%")],
                )
                + alt.Chart(monthly_long)
                .mark_line(interpolate="monotone", strokeWidth=3)
                .encode(
                    x=alt.X("month:T", title="Month"),
                    y=alt.Y("value:Q", title="Rate"),
                    color=alt.Color("metric:N", title="Metric", scale=alt.Scale(range=["#1DB954", "#BB86FC"])),
                    tooltip=["month:T", "metric:N", alt.Tooltip("value:Q", format=".2%")],
                )
                + alt.Chart(monthly_long)
                .mark_circle(size=70, stroke="#050505", strokeWidth=1.4)
                .encode(
                    x=alt.X("month:T", title="Month"),
                    y=alt.Y("value:Q", title="Rate"),
                    color=alt.Color("metric:N", title="Metric", scale=alt.Scale(range=["#1DB954", "#BB86FC"])),
                    tooltip=["month:T", "metric:N", alt.Tooltip("value:Q", format=".2%")],
                )
            )
            monthly_chart = monthly_chart.properties(height=360)
            st.altair_chart(chart_style(monthly_chart), use_container_width=True)
            st.dataframe(monthly, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.markdown('<div class="section-title">Song lifecycle explorer</div>', unsafe_allow_html=True)
        display = filtered_lifecycle[
            [
                "album_cover_url",
                "song",
                "artist",
                "release_form",
                "explicit_label",
                "entry_date",
                "exit_date",
                "observed_days",
                "calendar_span_days",
                "retention_ratio",
                "peak_position",
                "entry_to_peak_days",
                "avg_popularity",
                "duration_min",
                "total_tracks",
            ]
        ].sort_values(["observed_days", "peak_position"], ascending=[False, True])
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "album_cover_url": st.column_config.ImageColumn("Cover", width="small"),
                "entry_date": st.column_config.DateColumn("Entry"),
                "exit_date": st.column_config.DateColumn("Exit"),
                "retention_ratio": st.column_config.NumberColumn("Retention ratio", format="%.2f"),
                "avg_popularity": st.column_config.NumberColumn("Avg popularity", format="%.1f"),
                "duration_min": st.column_config.NumberColumn("Duration min", format="%.2f"),
            },
        )

    with tabs[6]:
        st.markdown('<div class="section-title">Raw data validation</div>', unsafe_allow_html=True)
        st.dataframe(validation, use_container_width=True, hide_index=True)
        failed = validation[~validation["passes_50_rule"]]
        if len(failed):
            st.write("Dates failing the 50-entry rule")
            st.dataframe(failed, use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="page-footer">Made with ❤️ by <a href="https://github.com/Sunny210405" target="_blank">SUNNY</a> &nbsp;•&nbsp; Spain50 Analytics</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
