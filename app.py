from __future__ import annotations

from contextlib import contextmanager
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
PARENT_JS = """
(function() {
    try {
        if (window.__script_injected) return;
        window.__script_injected = true;
        
        console.log('Scroll and metric animation script starting in main window context...');
        
        const scrollObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                } else {
                    entry.target.classList.remove('in-view');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -40px 0px'
        });

        const setupScrollAnimations = () => {
            const markers = document.querySelectorAll('.chart-marker:not([data-processed=true])');
            markers.forEach(marker => {
                marker.setAttribute('data-processed', 'true');
                const chartType = marker.getAttribute('data-chart-type');
                
                const container = marker.closest('div[data-testid=element-container]');
                if (!container) return;
                
                let chartEl = null;
                let sibling = container.nextElementSibling;
                let count = 0;
                while (sibling && count < 3) {
                    chartEl = sibling.querySelector('div[data-testid=stAltairChart]');
                    if (chartEl) break;
                    sibling = sibling.nextElementSibling;
                    count++;
                }
                
                if (!chartEl) return;
                
                chartEl.classList.add('scroll-animate');
                if (chartType === 'bar') {
                    chartEl.classList.add('scroll-animate-bar');
                } else if (chartType === 'donut') {
                    chartEl.classList.add('scroll-animate-donut');
                } else {
                    chartEl.classList.add('scroll-animate-default');
                }
                
                scrollObserver.observe(chartEl);
            });
            
            const wrappers = document.querySelectorAll('div[data-testid=stVerticalBlockBorderWrapper]:not([data-observed=true])');
            wrappers.forEach(wrapper => {
                wrapper.setAttribute('data-observed', 'true');
                wrapper.classList.add('scroll-animate', 'scroll-animate-default');
                scrollObserver.observe(wrapper);
            });
        };

        const animateElement = (el) => {
            const targetVal = parseFloat(el.getAttribute('data-val'));
            if (isNaN(targetVal)) return;

            const lastVal = parseFloat(el.dataset.lastVal);
            if (lastVal === targetVal) {
                return;
            }
            el.dataset.lastVal = targetVal;

            const animToken = Math.random().toString();
            el.dataset.animToken = animToken;

            const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
            const suffix = el.getAttribute('data-suffix') || '';
            const duration = 1000;
            const startTime = performance.now();
            
            const update = (now) => {
                if (el.dataset.animToken !== animToken) return;

                const elapsed = now - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                const currentVal = easeProgress * targetVal;
                
                let formatted = '';
                if (decimals === 0) {
                    formatted = Math.floor(currentVal).toLocaleString();
                } else {
                    const fixed = currentVal.toFixed(decimals);
                    const parts = fixed.split('.');
                    parts[0] = parseInt(parts[0], 10).toLocaleString();
                    formatted = parts.join('.');
                }
                
                el.textContent = formatted + suffix;
                
                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    let finalFormatted = '';
                    if (decimals === 0) {
                        finalFormatted = targetVal.toLocaleString();
                    } else {
                        const fixed = targetVal.toFixed(decimals);
                        const parts = fixed.split('.');
                        parts[0] = parseInt(parts[0], 10).toLocaleString();
                        finalFormatted = parts.join('.');
                    }
                    el.textContent = finalFormatted + suffix;
                }
            };
            requestAnimationFrame(update);
        };

        const animateAll = () => {
            const els = document.querySelectorAll('.metric-value[data-val], .maturity-metric-value[data-val]');
            els.forEach(el => animateElement(el));
        };

        const metricObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const el = entry.target;
                if (entry.isIntersecting) {
                    animateElement(el);
                } else {
                    delete el.dataset.lastVal;
                }
            });
        }, {
            threshold: 0.05
        });

        const setupMetricObservers = () => {
            const els = document.querySelectorAll('.metric-value[data-val], .maturity-metric-value[data-val]');
            els.forEach(el => {
                if (!el.dataset.observed) {
                    el.dataset.observed = 'true';
                    metricObserver.observe(el);
                }
            });
        };

        const mutationObserver = new MutationObserver((mutations) => {
            let shouldAnimate = false;
            let domChanged = false;
            for (let mutation of mutations) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-val') {
                    shouldAnimate = true;
                }
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    domChanged = true;
                }
            }
            if (shouldAnimate) {
                animateAll();
            }
            if (domChanged) {
                setupScrollAnimations();
                setupMetricObservers();
            }
        });

        mutationObserver.observe(document.body, {
            attributes: true,
            childList: true,
            subtree: true,
            attributeFilter: ['data-val']
        });

        setTimeout(() => {
            setupScrollAnimations();
            setupMetricObservers();
        }, 100);

    } catch(e) {
        console.error('Scroll/Metric animation failed in main context:', e);
    }
})();
"""


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
        [data-testid="stDownloadButton"] button, [data-testid="stDownloadButton"] button p,
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
            background: #050505;
            color: var(--text);
        }

        /* Animated aurora background blobs */
        .stApp::before,
        .stApp::after {
            content: '';
            position: fixed;
            border-radius: 50%;
            filter: blur(70px);
            pointer-events: none;
            z-index: 0;
        }

        /* Blob 1 — pinned top-left */
        .stApp::before {
            width: 750px;
            height: 750px;
            background: radial-gradient(circle, rgba(29,185,84,0.35) 0%, rgba(29,185,84,0.10) 50%, transparent 70%);
            top: 0;
            left: 0;
            transform-origin: top left;
            animation: blobDrift1 12s ease-in-out infinite alternate;
        }

        /* Blob 2 — pinned bottom-right, kept faint so it doesn't overpower content */
        .stApp::after {
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(29,185,84,0.22) 0%, rgba(16,120,50,0.07) 60%, transparent 80%);
            bottom: 0;
            right: 0;
            transform-origin: bottom right;
            animation: blobDrift2 15s ease-in-out infinite alternate;
        }

        /* Third blob — center screen, very faint */
        [data-testid="stAppViewContainer"]::before {
            content: '';
            position: fixed;
            width: 500px;
            height: 500px;
            border-radius: 50%;
            filter: blur(100px);
            pointer-events: none;
            z-index: 0;
            background: radial-gradient(circle, rgba(29,185,84,0.07) 0%, transparent 70%);
            top: 45%;
            left: 50%;
            transform: translateX(-50%);
            animation: blobDrift3 20s ease-in-out infinite alternate;
        }

        @keyframes blobDrift1 {
            0%   { transform: translate(0px, 0px) scale(1);    opacity: 0.85; }
            33%  { transform: translate(100px, 70px) scale(1.18); opacity: 1; }
            66%  { transform: translate(-50px, 130px) scale(0.9); opacity: 0.75; }
            100% { transform: translate(70px, -50px) scale(1.12); opacity: 0.95; }
        }

        @keyframes blobDrift2 {
            0%   { transform: translate(0px, 0px) scale(1);     opacity: 0.7; }
            33%  { transform: translate(-80px, -90px) scale(1.15); opacity: 0.95; }
            66%  { transform: translate(60px, -50px) scale(0.88);  opacity: 0.7; }
            100% { transform: translate(-40px, 80px) scale(1.1);  opacity: 0.85; }
        }

        @keyframes blobDrift3 {
            0%   { transform: translateX(-50%) scale(1);    opacity: 0.5; }
            50%  { transform: translateX(-50%) translate(80px, -60px) scale(1.2); opacity: 0.75; }
            100% { transform: translateX(-50%) translate(-60px, 50px) scale(0.9); opacity: 0.55; }
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
            background: rgba(5, 5, 5, 0.55) !important;
            backdrop-filter: blur(24px) saturate(1.4) !important;
            -webkit-backdrop-filter: blur(24px) saturate(1.4) !important;
            border-right: 1px solid rgba(29,185,84,0.15) !important;
            box-shadow: 4px 0 32px rgba(0,0,0,0.4);
        }

        /* Also target the inner content wrapper Streamlit wraps the sidebar in */
        [data-testid="stSidebar"] > div:first-child {
            background: transparent !important;
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

        /* Style the outer wrapper containers instead of the inner input to prevent double borders */
        [data-testid="stSidebar"] .stTextInput [data-baseweb="input"],
        [data-testid="stSidebar"] .stDateInput [data-baseweb="input"],
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: #121212 !important;
            border: 1px solid rgba(255,255,255,.08) !important;
            border-radius: 8px !important;
            transition: border-color 0.25s ease !important;
        }

        [data-testid="stSidebar"] .stTextInput [data-baseweb="input"]:focus-within,
        [data-testid="stSidebar"] .stDateInput [data-baseweb="input"]:focus-within,
        [data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
            border-color: rgba(29, 185, 84, 0.5) !important;
        }

        /* Reset the inner input tags to prevent double borders/padding */
        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] .stDateInput input {
            border: none !important;
            background: transparent !important;
            outline: none !important;
            box-shadow: none !important;
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
            border-radius: 16px;
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
            text-align: center;
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
            max-width: 100%;
            white-space: nowrap;
            font-size: 1rem;
            line-height: 1.55;
            margin: .7rem 0 0;
            text-align: center;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: .8rem;
            margin: 1.75rem 0 .85rem;
        }

        .metric-card {
            background: linear-gradient(to bottom, rgba(29, 185, 84, 0.12) 0%, var(--panel) 50%, var(--panel) 100%) !important;
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: .95rem .95rem .9rem;
            min-height: 98px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            animation: fadeUp .45s ease both;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        .metric-card:hover {
            background: linear-gradient(to bottom, rgba(29, 185, 84, 0.22) 0%, var(--panel-2) 50%, var(--panel-2) 100%) !important;
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
            color: var(--accent);
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
            border: 1px solid rgba(235,87,87,.45);
            background: rgba(235,87,87,.10);
            color: #ffb3b3;
            border-radius: 8px;
            padding: .85rem 1rem;
            margin: .75rem 0 1rem;
            font-weight: 650;
            animation: fadeUp .55s ease both;
        }

        /* Validation tab — red accent on 7th tab button */
        [data-testid="stTabs"] [data-baseweb="tab-list"] button:nth-child(7) {
            color: #ff6b6b !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab-list"] button:nth-child(7)[aria-selected="true"] {
            color: #ff4444 !important;
            border-bottom-color: #ff4444 !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab-list"] button:nth-child(7):hover {
            color: #ff4444 !important;
            background: rgba(235,87,87,.10) !important;
        }

        /* Report tab — header banner */
        .report-header {
            background: linear-gradient(135deg, rgba(29,185,84,.13) 0%, rgba(29,185,84,.04) 100%);
            border: 1px solid rgba(29,185,84,.22);
            border-radius: 14px;
            padding: 1.4rem 1.8rem 1.2rem;
            margin: .25rem 0 1.2rem;
            display: flex;
            flex-direction: column;
            gap: .55rem;
            animation: fadeUp .4s ease both;
        }
        .report-header-title {
            font-size: 1.35rem;
            font-weight: 900;
            color: var(--text);
            letter-spacing: -.01em;
            line-height: 1.2;
            margin: 0 0 .3rem;
        }
        .report-header-subtitle {
            color: var(--muted);
            font-size: .9rem;
            margin: 0;
            max-width: 700px;
            line-height: 1.55;
        }
        .report-badges {
            display: flex;
            gap: .5rem;
            flex-wrap: wrap;
            margin-top: .45rem;
        }
        .report-badge {
            background: rgba(255,255,255,.07);
            border: 1px solid rgba(255,255,255,.1);
            border-radius: 20px;
            padding: .22rem .75rem;
            font-size: .76rem;
            font-weight: 700;
            color: #b0b0b0;
            letter-spacing: .02em;
        }
        .report-badge.green {
            background: rgba(29,185,84,.12);
            border-color: rgba(29,185,84,.3);
            color: #1DB954;
        }

        /* Download button — exact match of st.button() */
        [data-testid="stDownloadButton"] button {
            background: linear-gradient(135deg, #1DB954 0%, #17a349 100%) !important;
            color: #000 !important;
            border: none !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
            box-shadow: none !important;
            border-radius: 0.5rem !important;
            padding: 0.25rem 0.75rem !important;
            min-height: 2.5rem !important;
            line-height: 1.6 !important;
            transition: filter .15s ease, transform .15s ease !important;
        }
        [data-testid="stDownloadButton"] button:hover {
            filter: brightness(0.92) !important;
            transform: translateY(-1px) !important;
        }

        /* Report content box — rounded glassmorphism container */
        .report-content-box {
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(255,255,255,.09);
            border-radius: 16px;
            padding: 1.8rem 2rem;
            margin-top: 1rem;
            line-height: 1.75;
        }
        .report-content-box h1,
        .report-content-box h2 {
            color: #f5f5f5;
            border-bottom: 1px solid rgba(255,255,255,.08);
            padding-bottom: .4rem;
            margin-top: 1.6rem;
            margin-bottom: .7rem;
        }
        .report-content-box h3 {
            color: #1DB954;
            margin-top: 1.2rem;
            margin-bottom: .45rem;
        }
        .report-content-box p {
            color: #d0d0d0;
            margin-bottom: .75rem;
        }
        .report-content-box ul, .report-content-box ol {
            color: #d0d0d0;
            padding-left: 1.4rem;
            margin-bottom: .75rem;
        }
        .report-content-box li {
            margin-bottom: .35rem;
        }
        .report-content-box strong {
            color: #f5f5f5;
        }
        .report-content-box code {
            background: rgba(29,185,84,.12);
            color: #1DB954;
            padding: .1em .4em;
            border-radius: 4px;
            font-size: .9em;
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
            background: #181818;
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
            background: transparent;
            border: none;
            padding: 0;
            animation: none;
            box-shadow: none;
        }

        /* ── Chart panel (glass tab) ──
           Simplifying selectors to directly target the wrapper and children. */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #181818 !important;
            background-color: #181818 !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
            animation: fadeUp .5s ease both;
            transition: box-shadow 0.3s cubic-bezier(0.25, 0.8, 0.25, 1),
                        border-color 0.3s ease !important;
            padding: 0 !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(29, 185, 84, 0.3) !important;
            box-shadow: 0 12px 42px rgba(29, 185, 84, 0.1),
                        inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
        }

        /* Make all intermediate layout containers inside the border wrapper transparent. */
        div[data-testid="stVerticalBlockBorderWrapper"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"] div.stVerticalBlock,
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="element-container"],
        div[data-testid="stVerticalBlockBorderWrapper"] div.element-container,
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stMarkdownContainer"] {
            background: transparent !important;
            background-color: transparent !important;
            padding: 0 !important;
            gap: 0 !important;
        }

        /* Panel title — plain label, no dot, no coloured background */
        .cp-header {
            padding: 0.65rem 1rem 0.6rem;
            border-bottom: 1px solid rgba(255,255,255,0.07);
            margin: 0 0 0.5rem;
        }

        .cp-header-title {
            color: var(--muted);
            font-size: 0.80rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }

        /* Validation tab header */
        .cp-header-red {
            padding: 0.65rem 1rem 0.6rem;
            border-bottom: 1px solid rgba(235,87,87,0.18);
            margin: 0 0 0.5rem;
        }

        .cp-header-red-title {
            color: #ff6b6b;
            font-size: 0.80rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
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

        /* ── Scroll Animation System ── */
        .scroll-animate {
            opacity: 0;
            filter: blur(5px);
            transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1),
                        transform 0.8s cubic-bezier(0.16, 1, 0.3, 1),
                        clip-path 1.2s cubic-bezier(0.16, 1, 0.3, 1),
                        filter 0.8s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }

        /* Disable the default on-load fadeUp animation on stVerticalBlockBorderWrapper if JS is active */
        div[data-testid="stVerticalBlockBorderWrapper"].scroll-animate {
            animation: none !important;
        }

        .scroll-animate-default {
            transform: translateY(35px);
        }
        .scroll-animate-default.in-view {
            opacity: 1;
            transform: translateY(0);
            filter: blur(0);
        }

        /* Bar chart specific: growing from left to right using clip-path */
        .scroll-animate-bar {
            clip-path: inset(0 100% 0 0);
            transform: scale(0.98);
        }
        .scroll-animate-bar.in-view {
            opacity: 1;
            clip-path: inset(0 0 0 0);
            transform: scale(1);
            filter: blur(0);
        }

        /* Donut chart specific: scale up and spin slightly */
        .scroll-animate-donut {
            transform: scale(0.8) rotate(-15deg);
        }
        .scroll-animate-donut.in-view {
            opacity: 1;
            transform: scale(1) rotate(0deg);
            filter: blur(0);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.html("<script>" + PARENT_JS + "</script>", unsafe_allow_javascript=True)


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
    return chart.configure(background="transparent").configure_view(
        strokeWidth=0,
        fill="rgba(13,13,13,0.45)",
        stroke=None,
    ).configure_axis(
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



@contextmanager
def chart_panel(title: str, red: bool = False):
    """Context manager: renders children inside a native Streamlit bordered
    container (st.container(border=True)), which creates a real DOM wrapper
    (stVerticalBlockBorderWrapper) that our CSS can reliably style.
    """
    header_cls  = "cp-header-red"   if red else "cp-header"
    title_cls   = "cp-header-red-title" if red else "cp-header-title"
    with st.container(border=True):
        st.markdown(
            f'<div class="{header_cls}">'
            f'<span class="{title_cls}">{escape(title)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        yield


def render_metric_grid(metrics: list[tuple[str, str, str]]) -> None:
    cards = "\n".join(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>'
        for label, value, note in metrics
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def latest_unique_artwork(rows: pd.DataFrame, limit: int = 6, by_cover: bool = False) -> pd.DataFrame:
    if rows.empty:
        return rows
    latest_date = rows["date_dt"].max()
    dup_col = "album_cover_url" if by_cover else "song_key"
    return (
        rows[rows["date_dt"].eq(latest_date)]
        .sort_values("position")
        .drop_duplicates(dup_col)
        .head(limit)
    )




def render_album_rail(rows: pd.DataFrame, title: str = "Latest playlist covers") -> None:
    if rows.empty:
        return
    cards = []
    is_expanded = len(rows) > 6
    for idx, (_, row) in enumerate(rows.iterrows()):
        cover_url = str(row["album_cover_url"])
        
        # Staggered animation delay for a premium cascading effect (cap delay to prevent long trails)
        delay_ms = min(idx * 20, 600) if is_expanded else idx * 30
        cards.append(
            "".join(
                [
                    f'<div class="album-card" style="animation-delay: {delay_ms}ms;">',
                    f'<img src="{escape(cover_url)}" alt="{escape(str(row["song"]))} album cover">',
                    f'<div class="album-rank">#{int(row["position"])}</div>',
                    f'<div class="album-title">{escape(str(row["song"]))}</div>',
                    f'<div class="album-artist">{escape(str(row["artist"]))}</div>',
                    "</div>",
                ]
            )
        )
    st.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="album-rail {"expanded" if is_expanded else "collapsed"}">{"".join(cards)}</div>', unsafe_allow_html=True)


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


def donut_chart(df: pd.DataFrame, category: str, value: str, color_key: str | None = None, title: str | None = None):
    chart_df = df.copy()
    scale = None
    if color_key == "explicit_label":
        scale = color_scale(EXPLICIT_COLORS)
    elif color_key == "release_form":
        scale = color_scale(RELEASE_COLORS)

    if color_key and scale:
        color_encoding = alt.Color(f"{category}:N", scale=scale, title=category.replace("_", " ").title())
    else:
        color_encoding = alt.Color(f"{category}:N", title=category.replace("_", " ").title())

    chart = (
        alt.Chart(chart_df)
        .mark_arc(innerRadius=50, outerRadius=90, stroke="#181818", strokeWidth=2)
        .encode(
            theta=alt.Theta(f"{value}:Q", stack=True),
            color=color_encoding,
            tooltip=[category, alt.Tooltip(f"{value}:Q", format=".1f")],
        )
        .properties(height=260)
    )
    if title:
        chart = chart.properties(title=title)
    return chart_style(chart)


def main() -> None:
    inject_global_styles()

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-title">Spain<span style="color: var(--accent);">50</span> Analytics</div>
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

    avg_days = filtered_lifecycle["observed_days"].mean() if len(filtered_lifecycle) else pd.NA
    peak_time = filtered_lifecycle["entry_to_peak_days"].mean() if len(filtered_lifecycle) else pd.NA
    churn_rate = filtered_churn["churn_rate"].dropna().mean() * 100
    stability = filtered_churn["retention_stability_index"].dropna().mean() * 100
    unique_songs = filtered_lifecycle["song_key"].nunique()
    playlist_days = filtered_stage["date_dt"].nunique()

    metrics = [
        ("Avg days", avg_days, "", 1),
        ("Entry to peak", peak_time, "", 1),
        ("Churn rate", churn_rate, "%", 1),
        ("Stability", stability, "%", 1),
        ("Songs", unique_songs, "", 0),
        ("Days", playlist_days, "", 0),
    ]

    card_list = []
    for label, val, suffix, dec in metrics:
        note = (
            "playlist survival" if label == "Avg days" else
            "maturity speed" if label == "Entry to peak" else
            "daily rotation" if label == "Churn rate" else
            "day-to-day overlap" if label == "Stability" else
            "filtered catalog" if label == "Songs" else
            "snapshots in range"
        )
        if pd.isna(val):
            card_list.append(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">n/a</div>'
                f'<div class="metric-note">{note}</div>'
                f'</div>'
            )
        else:
            formatted = fmt_num(val, suffix, dec)
            card_list.append(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value" data-val="{val}" data-suffix="{suffix}" data-decimals="{dec}">{formatted}</div>'
                f'<div class="metric-note">{note}</div>'
                f'</div>'
            )
    cards = "\n".join(card_list)

    st.markdown(
        f"""
        <section class="hero-shell">
            <h1 class="hero-title">Spain<span style="color: var(--accent);">50</span> Analytics</h1>
            <p class="hero-copy">Track entries, exits, maturity, and retention with album artwork, content filters, and release-form diagnostics for Spain's daily Top 50.</p>
            <div class="metric-grid">{cards}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if "show_all_covers" not in st.session_state:
        st.session_state["show_all_covers"] = False

    is_expanded = st.session_state["show_all_covers"]
    latest_artwork = latest_unique_artwork(filtered_stage, 50 if is_expanded else 6, by_cover=not is_expanded)
    
    render_album_rail(latest_artwork, "Latest filtered Top 50 covers")

    # Show dynamic action button below the rail to expand/shrink
    full_artwork_count = len(latest_unique_artwork(filtered_stage, 50, by_cover=False))
    if full_artwork_count > 6:
        _, btn_col, _ = st.columns([1.5, 1, 1.5])
        with btn_col:
            if is_expanded:
                if st.button("Show Less ↑", key="toggle_covers_btn", use_container_width=True):
                    st.session_state["show_all_covers"] = False
                    st.rerun()
            else:
                if st.button(f"Show All Top {full_artwork_count} ↓", key="toggle_covers_btn", use_container_width=True):
                    st.session_state["show_all_covers"] = True
                    st.rerun()

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
            "Executive Summary",
            "Research Paper",
        ]
    )

    with tabs[0]:
        left, right = st.columns([1, 1])
        with left:
            with chart_panel("Lifecycle Stage Distribution"):
                dist = stage_distribution(filtered_stage) if len(filtered_stage) else pd.DataFrame()
                if len(dist):
                    st.markdown('<div class="chart-marker" data-chart-type="bar"></div>', unsafe_allow_html=True)
                    st.altair_chart(bar_chart(dist, "stage", "observations", "stage"), use_container_width=True)
                else:
                    st.info("No rows match the selected filters.")
        with right:
            with chart_panel("Top Lifecycle Performers"):
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
            with chart_panel("Playlist Position Over Time"):
                st.markdown('<div class="chart-marker" data-chart-type="default"></div>', unsafe_allow_html=True)
                st.altair_chart(line_rank_chart(song_rows), use_container_width=True)
            with chart_panel("Daily Stage Breakdown"):
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
        with chart_panel("Daily Entry & Exit Flow"):
            st.markdown('<div class="chart-marker" data-chart-type="default"></div>', unsafe_allow_html=True)
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

        score_attr = f'data-val="{dyn_explicit_score:.2f}" data-suffix="x" data-decimals="2"' if not pd.isna(dyn_explicit_score) else ""
        ratio_attr = f'data-val="{dyn_single_album_ratio:.2f}" data-suffix="x" data-decimals="2"' if not pd.isna(dyn_single_album_ratio) else ""

        st.markdown(
            f"""
            <div class="maturity-metric-grid">
                <div class="maturity-metric-card">
                    <div class="maturity-metric-label">Explicit Content Lifecycle Score</div>
                    <div class="maturity-metric-value" {score_attr}>{score_str}</div>
                    <div class="maturity-metric-note">Explicit vs Clean average longevity ratio</div>
                </div>
                <div class="maturity-metric-card">
                    <div class="maturity-metric-label">Single vs Album Longevity Ratio</div>
                    <div class="maturity-metric-value" {ratio_attr}>{ratio_str}</div>
                    <div class="maturity-metric-note">Singles vs Album tracks longevity ratio</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_a, col_b = st.columns(2)
        with col_a:
            with chart_panel("Explicit vs Clean — Avg Longevity"):
                explicit_summary = attribute_summary(filtered_lifecycle, "explicit_label") if len(filtered_lifecycle) else pd.DataFrame()
                st.dataframe(explicit_summary, use_container_width=True, hide_index=True)
                if len(explicit_summary):
                    st.markdown('<div class="chart-marker" data-chart-type="donut"></div>', unsafe_allow_html=True)
                    st.altair_chart(donut_chart(explicit_summary, "explicit_label", "avg_days", "explicit_label"), use_container_width=True)
        with col_b:
            with chart_panel("Single vs Album — Avg Longevity"):
                release_summary = attribute_summary(filtered_lifecycle, "release_form") if len(filtered_lifecycle) else pd.DataFrame()
                st.dataframe(release_summary, use_container_width=True, hide_index=True)
                if len(release_summary):
                    st.markdown('<div class="chart-marker" data-chart-type="donut"></div>', unsafe_allow_html=True)
                    st.altair_chart(donut_chart(release_summary, "release_form", "avg_days", "release_form"), use_container_width=True)

        with chart_panel("Duration vs Retention Scatter"):
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
            st.markdown('<div class="chart-marker" data-chart-type="default"></div>', unsafe_allow_html=True)
            st.altair_chart(chart_style(duration_chart), use_container_width=True)

    with tabs[4]:
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
            with chart_panel("Monthly Rotation Profile"):
                st.markdown('<div class="chart-marker" data-chart-type="default"></div>', unsafe_allow_html=True)
                st.altair_chart(chart_style(monthly_chart), use_container_width=True)
            with chart_panel("Monthly Rotation Data"):
                st.dataframe(monthly, use_container_width=True, hide_index=True)

    with tabs[5]:
        with chart_panel("Song Lifecycle Explorer"):
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

    # ── Validation Tab (index 6) ───────────────────────────────────────────
    with tabs[6]:
        with chart_panel("⚠️ Raw Data Validation", red=True):
            st.dataframe(validation, use_container_width=True, hide_index=True)
            failed = validation[~validation["passes_50_rule"]]
            if len(failed):
                st.markdown(
                    '<div style="border:1px solid rgba(235,87,87,.45);background:rgba(235,87,87,.10);'
                    'color:#ffb3b3;border-radius:8px;padding:.65rem 1rem;margin:.5rem 0;font-weight:700;">'
                    f'⛔ {len(failed)} date(s) failing the 50-entry rule</div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(failed, use_container_width=True, hide_index=True)

    # ── Executive Summary Tab (index 7) ────────────────────────────────────
    with tabs[7]:
        from pathlib import Path as _Path
        _exec_path = _Path(__file__).resolve().parent / "reports" / "executive_summary.md"
        _exec_size = f"{_exec_path.stat().st_size // 1024 or 1} KB" if _exec_path.exists() else "—"
        _exec_body = _exec_path.read_text(encoding="utf-8") if _exec_path.exists() else ""
        _exec_dl_url = "executive_summary.md"

        # Download button — centered
        _dl7_gap1, _dl7_mid, _dl7_gap2 = st.columns([1, 2, 1])
        with _dl7_mid:
            if _exec_path.exists():
                st.download_button(
                    label="Download Report ↓",
                    data=_exec_path.read_bytes(),
                    file_name="executive_summary.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_exec_tab",
                )

        # Header card
        import html as _html_mod
        st.markdown(
            f"""
            <div class="report-header">
              <p class="report-header-title">🧾 Executive Summary</p>
              <p class="report-header-subtitle">
                A concise, stakeholder-ready overview of Atlantic Spain&#39;s playlist
                lifecycle findings — covering headline KPIs, strategic implications,
                and recommended actions for the Spain market.
              </p>
              <div class="report-badges">
                <span class="report-badge green">Atlantic Spain Top 50</span>
                <span class="report-badge">2024-05-18 → 2025-11-27</span>
                <span class="report-badge">555 playlist days</span>
                <span class="report-badge">{_exec_size} · Markdown</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if _exec_path.exists():
            st.markdown(
                f'<div class="report-content-box">\n\n{_exec_body}\n\n</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("executive_summary.md not found. Run `python generate_reports.py` first.")

    # ── Research Paper Tab (index 8) ──────────────────────────────────────
    with tabs[8]:
        from pathlib import Path as _Path
        _rp_path = _Path(__file__).resolve().parent / "reports" / "research_paper.md"
        _rp_size  = f"{_rp_path.stat().st_size // 1024 or 1} KB" if _rp_path.exists() else "—"
        _rp_body  = _rp_path.read_text(encoding="utf-8") if _rp_path.exists() else ""

        # Download button — centered
        _dl8_gap1, _dl8_mid, _dl8_gap2 = st.columns([1, 2, 1])
        with _dl8_mid:
            if _rp_path.exists():
                st.download_button(
                    label="Download Report ↓",
                    data=_rp_path.read_bytes(),
                    file_name="research_paper.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_rp_tab",
                )

        # Header card
        st.markdown(
            f"""
            <div class="report-header">
              <p class="report-header-title">📄 Research Paper</p>
              <p class="report-header-subtitle">
                Full analytical write-up covering data scope, validation methodology,
                lifecycle construction, KPI deep-dives, stage distribution, churn
                dynamics, explicit vs clean content behavior, and strategic recommendations.
              </p>
              <div class="report-badges">
                <span class="report-badge green">Atlantic Spain Top 50</span>
                <span class="report-badge">575 unique songs</span>
                <span class="report-badge">27,750 cleaned rows</span>
                <span class="report-badge">{_rp_size} · Markdown</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if _rp_path.exists():
            st.markdown(
                f'<div class="report-content-box">\n\n{_rp_body}\n\n</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("research_paper.md not found. Run `python generate_reports.py` first.")


    st.markdown(
        '<div class="page-footer">Made with ❤️ by <a href="https://github.com/Sunny210405" target="_blank">SUNNY</a> &nbsp;•&nbsp; Spain50 Analytics</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
