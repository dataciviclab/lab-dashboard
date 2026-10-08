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
st.markdown(
    """
<style>
.funnel-bar-bg { background: var(--secondary-background-color); }
.funnel-bar-fill { color: var(--text-color) !important; }
</style>
""",
    unsafe_allow_html=True,
)

# Logo + nome Lab in alto a sinistra
st.logo(
    "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg",
    size="large",
)

# Navigazione gerarchica
pages = {
    "": [
        st.Page("pages/00_Vista_Insieme.py", title="Vista d'insieme", icon="📊", default=True),
    ],
    "Source Observatory": [
        st.Page("pages/05_Radar.py", title="Radar", icon="📡"),
        st.Page("pages/06_Inventario.py", title="Inventario", icon="📦"),
        st.Page("pages/07_Fonte.py", title="Scheda fonte", icon="🔍"),
    ],
    "Catalogo": [
        st.Page("pages/02_Pipeline_Health.py", title="Registry / Repo", icon="📦"),
        st.Page("pages/01_Dataset_Explorer.py", title="Catalogo", icon="📚"),
        st.Page("pages/03_Analisi.py", title="Analisi", icon="🧩"),
        st.Page("pages/09_Query_SQL.py", title="Query SQL", icon="🧪"),
    ],
    "Community": [
        st.Page("pages/04_Community.py", title="PR · Issues · Discussions", icon="💬"),
    ],
}

pg = st.navigation(pages, position="sidebar")

st.sidebar.caption("")  # spazio leggero
st.sidebar.caption(
    "[DataCivicLab](https://dataciviclab.org/) · [Explorer](https://dataciviclab.github.io/data-explorer/)"
)
st.sidebar.caption(
    "[Discussioni](https://github.com/dataciviclab/dataciviclab/discussions) · [GitHub](https://github.com/dataciviclab)"
)

pg.run()
