#!/usr/bin/env python3
"""
DataCivicLab · Dashboard operativo interno.
Entry point — delega a pages/*.py per le sezioni.

Avvio: streamlit run app.py
"""
import streamlit as st

import os

st.set_page_config(
    page_title="DataCivicLab · Dashboard",
    page_icon="https://raw.githubusercontent.com/dataciviclab/dataciviclab/main/assets/logo.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar comune
st.logo(
    "https://raw.githubusercontent.com/dataciviclab/dataciviclab/main/assets/logo.svg",
    size="large",
)
st.sidebar.title("DataCivicLab")
st.sidebar.caption("Dashboard operativo")

# Auto-refresh toggle
_refresh = st.sidebar.toggle("🔄 Auto-refresh 60s", value=False, key="_autorefresh")
if _refresh:
    st.sidebar.caption("Ricarica ogni 60s")
    st.markdown(
        '<meta http-equiv="refresh" content="60">',
        unsafe_allow_html=True,
    )

# Dark mode toggle
_dark = st.sidebar.toggle("🌙 Dark mode", value=False, key="_darkmode")
if _dark:
    st.markdown("""
        <style>
        /* Forza dark mode app */
        .stApp { background-color: #0e1117; }
        .stApp header, .stApp footer { background-color: #0e1117 !important; }
        /* Custom funnel bars in dark mode */
        .funnel-bar-bg { background: #262730 !important; }
        .funnel-bar-fill { color: #fff !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .funnel-bar-bg { background: #f0f0f0 !important; }
        .funnel-bar-fill { color: #fff !important; }
        </style>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "Dati: [dataset-incubator/registry]"
    "(https://github.com/dataciviclab/dataset-incubator/tree/main/registry) · "
    "GCS parquet"
)

# La home page mostra una welcome; le pagine sono in pages/
st.title("DataCivicLab · Dashboard")
st.markdown(
    "Dashboard operativo interno del Lab.\n\n"
    "Seleziona una sezione dal menu a sinistra."
)

col1, col2, col3 = st.columns(3)
col1.info("📦 **Dataset** · 24+ nel catalogo")
col2.info("🔍 **Fonti** · 23+ monitorate")
col3.info("⚙️ **Pipeline** · stato in tempo reale")
