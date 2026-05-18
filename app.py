#!/usr/bin/env python3
"""
DataCivicLab · Dashboard operativo interno.
Entry point — delega a pages/*.py per le sezioni.

Avvio: streamlit run app.py
"""
import streamlit as st
from sources import LOGO_URL

st.set_page_config(
    page_title="DataCivicLab · Dashboard",
    page_icon=LOGO_URL,
    layout="wide",
)

# Logo — visibile su tutte le pagine (Streamlit lo mantiene in navbar)
st.logo(LOGO_URL, size="large")

# CSS globale per componenti custom (funnel bars)
st.markdown("""
<style>
.stApp > header, section[data-testid="stSidebar"] > div:first-child {
    background: var(--background-color) !important;
}
.funnel-bar-bg { background: var(--secondary-background-color); }
.funnel-bar-fill { color: var(--text-color) !important; }
</style>
""", unsafe_allow_html=True)

st.title("DataCivicLab · Dashboard")
st.markdown("Seleziona una sezione dal menu a sinistra.")

col1, col2, col3 = st.columns(3)
col1.info("📦 **Dataset** · 24+ nel catalogo")
col2.info("🔍 **Fonti** · 23+ monitorate")
col3.info("⚙️ **Pipeline** · stato in tempo reale")
