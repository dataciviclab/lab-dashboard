#!/usr/bin/env python3
"""
DataCivicLab · Dashboard
Navigazione gerarchica per Source Observatory, Dataset Incubator, Catalogo, Community.
"""
import streamlit as st

st.set_page_config(
    page_title="DataCivicLab · Dashboard",
    page_icon="https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg",
    layout="wide",
)

# CSS globali
st.markdown("""
<style>
.funnel-bar-bg { background: var(--secondary-background-color); }
.funnel-bar-fill { color: var(--text-color) !important; }
</style>
""", unsafe_allow_html=True)

# Logo in alto a sinistra
st.logo("https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg",
        size="large")

# Navigazione gerarchica
pages = {
    "": [
        st.Page("pages/00_Vista_Insieme.py", title="Vista d'insieme", icon="📊", default=True),
    ],
    "Source Observatory": [
        st.Page("pages/05_Source_Observatory.py", title="Stato e KPI", icon="🔭"),
    ],
    "Dataset Incubator": [
        st.Page("pages/02_Pipeline_Health.py", title="Pipeline CI", icon="⚙️"),
        st.Page("pages/04_Funnel_Candidate.py", title="Funnel candidate", icon="📥"),
        st.Page("pages/03_Copertura_Dati.py", title="Copertura dati", icon="📅"),
    ],
    "Catalogo": [
        st.Page("pages/01_Dataset_Explorer.py", title="Esplora dataset", icon="📚"),
    ],
    "Community": [
        st.Page("pages/06_Discussioni.py", title="Discussioni", icon="💬"),
    ],
}

pg = st.navigation(pages, position="sidebar")

# Sidebar comune: widget sotto il menu di navigazione
refresh = st.sidebar.toggle(
    "🔄 Ricarica 60s",
    value=st.session_state.get("autorefresh", False),
    key="ar_global",
)
st.session_state.autorefresh = refresh
if refresh:
    st.markdown(
        '<meta http-equiv="refresh" content="60">',
        unsafe_allow_html=True,
    )
st.sidebar.markdown("---")
st.sidebar.caption("🌙 **Tema scuro**: ☰ → Settings → Theme")
st.sidebar.caption(
    "💬 [Discussioni](https://github.com/dataciviclab/dataciviclab/discussions)"
    " · [Explorer](https://dataciviclab.github.io/data-explorer/)"
)
st.sidebar.caption(
    "📦 [dataset-incubator/registry]"
    "(https://github.com/dataciviclab/dataset-incubator/tree/main/registry)"
)

pg.run()
