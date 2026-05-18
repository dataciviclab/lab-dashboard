#!/usr/bin/env python3
"""
DataCivicLab · Dashboard — lo stato del Laboratorio in un colpo d'occhio.
"""
import streamlit as st
from sources import (
    LOGO_URL, load_catalog, load_signals, load_radar,
    render_sidebar_common, data_freshness_note,
    load_recent_discussions, load_discussion_counts,
)

st.set_page_config(
    page_title="DataCivicLab · Stato del Laboratorio",
    page_icon=LOGO_URL,
    layout="wide",
)

st.logo(LOGO_URL, size="large")

st.markdown("""
<style>
.funnel-bar-bg { background: var(--secondary-background-color); }
.funnel-bar-fill { color: var(--text-color) !important; }
</style>
""", unsafe_allow_html=True)

render_sidebar_common()

st.title("DataCivicLab · Stato del Laboratorio")
st.markdown(
    "Cosa stiamo facendo: dati, fonti e analisi in un colpo d'occhio."
)

# ── Carica dati ───────────────────────────────────────────────────────────────
catalog = load_catalog()
signals = load_signals()
radar = load_radar()
discussions = load_recent_discussions(5)
disc_counts = load_discussion_counts()

datasets = catalog.get("datasets", [])
sig_summary = signals.get("summary", {})
radar_status = radar.get("status_counts", {})

n_datasets = len(datasets)
n_published = sum(1 for d in datasets if d.get("stage") == "published")
n_incubating = sum(1 for d in datasets if d.get("stage") == "incubating")
n_ok = sig_summary.get("by_status", {}).get("ok", 0)
n_green = radar_status.get("GREEN", 0)
n_red = radar_status.get("RED", 0)
n_disc = disc_counts.get("totale", 0)

# ── Metriche ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Dataset", f"{n_datasets} totali",
            f"{n_published} pubblicati · {n_incubating} in corso")
col2.metric("🟢 Fonti attive", n_green,
            f"{n_red} non raggiungibili")
col3.metric("💬 Discussioni", n_disc,
            "pubbliche, in tutte le categorie")
col4.metric("✅ Pipeline OK", n_ok)

st.markdown("---")

# ── Novità recenti dalle discussion ──────────────────────────────────────────
if discussions:
    st.subheader("💬 Novità recenti")
    for d in discussions:
        cat = d.get("category", {}).get("name", "?")
        emoji = {"Analisi": "📊", "Domanda": "❓", "Datasets": "📦", "Annunci": "📢"}.get(cat, "💬")
        title = d.get("title", "")
        url = d.get("url", "")
        date = d.get("createdAt", "")[:10]
        st.write(f"{emoji} **[{cat}]** [{title}]({url}) · {date}")
    st.markdown("---")

# ── Dataset nel catalogo ─────────────────────────────────────────────────────
st.subheader("📦 Dataset nel catalogo")
for ds in datasets[:8]:
    period = ds.get("period", {})
    yrs = f"{period.get('start', '?')}–{period.get('end', '?')}" if period else "?"
    emoji = "✅" if ds.get("stage") == "published" else "🔬"
    st.write(f"{emoji} **{ds['slug']}** · {ds.get('stage', '?')} · {yrs}")

data_freshness_note()
