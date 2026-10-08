"""Analisi pubblicate — collezione Analisi del Lab collegate ai dataset."""

import pandas as pd
import streamlit as st

from sources import data_freshness_note, de_slug, load_analyses

st.title("🧩 Analisi")
st.markdown("Le analisi pubblicate del Lab, collegate ai dataset che usano.")

analyses = load_analyses()

if not analyses:
    st.error("Analisi non disponibili.")
    st.stop()

# ── KPI ─────────────────────────────────────────────────────────
n_total = len(analyses)
n_published = sum(1 for a in analyses if a.get("status") == "published")
sources = {a.get("source", "") for a in analyses if a.get("source")}

col1, col2, col3 = st.columns(3)
col1.metric("🧩 Analisi", n_total)
col2.metric("✅ Pubblicate", n_published)
col3.metric("🏷️ Fonti", len(sources))

st.markdown("---")

# ── Filtri ───────────────────────────────────────────────────────
search = st.text_input("Cerca", placeholder="nome, slug, descrizione...", key="an_search")
src_filter = st.selectbox(
    "Fonte",
    ["Tutte"] + sorted(sources),
    key="an_src",
)

filtered = analyses
if src_filter != "Tutte":
    filtered = [a for a in filtered if a.get("source") == src_filter]
if search:
    q = search.lower()
    filtered = [
        a
        for a in filtered
        if q in a.get("slug", "").lower()
        or q in a.get("name", "").lower()
        or q in a.get("description", "").lower()
    ]

st.write(f"**{len(filtered)} analisi** trovate")

# ── Lista analisi ────────────────────────────────────────────────
for a in filtered:
    datasets = a.get("datasets", [])
    ds_links = " · ".join(
        f"[{de_slug(d)}](https://dataciviclab.github.io/data-explorer/dataset/{de_slug(d)})"
        for d in datasets
    )
    period = f" · {a['period']}" if a.get("period") else ""
    status_icon = "✅" if a.get("status") == "published" else "🔬"
    with st.container(border=True):
        st.markdown(f"#### {status_icon} {a.get('name', a.get('slug', '?'))}")
        st.caption(f"{a.get('source', '—')}{period}")
        st.markdown(a.get("description", ""))
        if ds_links:
            st.markdown(f"📊 Dataset: {ds_links}")

# ── Tabella riepilogativa ────────────────────────────────────────
with st.expander("📋 Tabella riepilogativa"):
    df = pd.DataFrame(
        [
            {
                "slug": a.get("slug", ""),
                "nome": a.get("name", ""),
                "fonte": a.get("source", ""),
                "periodo": a.get("period", ""),
                "dataset": len(a.get("datasets", [])),
                "status": a.get("status", ""),
            }
            for a in filtered
        ]
    )
    st.dataframe(df, hide_index=True, width="stretch")

data_freshness_note()
