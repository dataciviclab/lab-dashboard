#!/usr/bin/env python3
"""
DataCivicLab · Dashboard operativo interno.
Entry point — homepage con panoramica live.
"""
import streamlit as st
from sources import LOGO_URL, load_catalog, load_signals, load_radar, render_sidebar_common, data_freshness_note

st.set_page_config(
    page_title="DataCivicLab · Dashboard",
    page_icon=LOGO_URL,
    layout="wide",
)

# CSS globale
st.markdown("""
<style>
.funnel-bar-bg { background: var(--secondary-background-color); }
.funnel-bar-fill { color: var(--text-color) !important; }
</style>
""", unsafe_allow_html=True)

# Sidebar + logo (stesso codice di tutte le altre pagine)
render_sidebar_common()

st.title("DataCivicLab · Dashboard")
st.markdown("Panoramica live dello stato del Laboratorio.")

# ── Carica dati live ──────────────────────────────────────────────────────────
catalog = load_catalog()
signals = load_signals()
radar = load_radar()

datasets = catalog.get("datasets", [])
sig_summary = signals.get("summary", {})
radar_status = radar.get("status_counts", {})

n_datasets = len(datasets)
n_published = sum(1 for d in datasets if d.get("stage") == "published")
n_incubating = sum(1 for d in datasets if d.get("stage") == "incubating")
n_ok = sig_summary.get("by_status", {}).get("ok", 0)
n_green = radar_status.get("GREEN", 0)
n_red = radar_status.get("RED", 0)

# ── Metriche ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Dataset totali", n_datasets,
            f"{n_published} pubblicati · {n_incubating} in incubazione")
col2.metric("✅ Pipeline OK", n_ok)
col3.metric("🟢 Fonti attive", n_green)
col4.metric("🔴 Fonti giù", n_red)

st.markdown("---")

# ── Sezioni rapide ────────────────────────────────────────────────────────────
st.subheader("Vai a")
cols = st.columns(3)
with cols[0]:
    st.page_link("home.py", label="🏠 Home", use_container_width=True)
    st.page_link("pages/00_Vista_Insieme.py", label="📊 Vista d'insieme", use_container_width=True)
    st.page_link("pages/01_Dataset_Explorer.py", label="🔍 Dataset Explorer", use_container_width=True)
with cols[1]:
    st.page_link("pages/04_Funnel_Candidate.py", label="🎯 Funnel Candidate", use_container_width=True)
    st.page_link("pages/05_Radar_Fonti.py", label="📡 Radar Fonti", use_container_width=True)
with cols[2]:
    st.page_link("pages/02_Pipeline_Health.py", label="⚙️ Pipeline Health", use_container_width=True)
    st.page_link("pages/03_Copertura_Dati.py", label="📅 Copertura Dati", use_container_width=True)

st.markdown("---")

# ── Ultimi dataset aggiornati ────────────────────────────────────────────────
st.subheader("Ultimi aggiornamenti")
recent = sorted(datasets, key=lambda d: d.get("updated_at", ""), reverse=True)[:8]
for ds in recent:
    emoji = "✅" if ds.get("stage") == "published" else "🔬"
    st.write(f"{emoji} **{ds['slug']}** — {ds.get('stage', '?')} · {ds.get('updated_at', '?')}")

data_freshness_note()
