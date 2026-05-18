#!/usr/bin/env python3
"""
DataCivicLab · Dashboard operativo interno.
Entry point — delega a pages/*.py per le sezioni.

Avvio: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="DataCivicLab · Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar comune (tutte le pagine ereditano questa configurazione)
st.logo(
    "https://raw.githubusercontent.com/dataciviclab/dataciviclab/main/assets/logo.svg"
)
st.sidebar.title("DataCivicLab")
st.sidebar.caption("Dashboard operativo")
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
