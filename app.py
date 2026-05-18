#!/usr/bin/env python3
"""
DataCivicLab · Dashboard operativo interno.
Entry point — delega a pages/*.py per le sezioni.

Avvio: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="DataCivicLab · Dashboard",
    page_icon="https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar comune
st.logo(
    "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg",
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

# CSS che si adatta automaticamente al tema nativo (sia light che dark)
st.markdown("""
<style>
.funnel-bar-bg { background: var(--secondary-background-color); }
.funnel-bar-fill { color: var(--text-color) !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.caption("🌙 **Tema**: ☰ menu → Settings → Theme")
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
