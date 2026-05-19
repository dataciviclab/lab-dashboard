"""Vista d'insieme — metriche aggregate da clean_catalog.json e pipeline_signals.json."""
import streamlit as st
import pandas as pd
from sources import load_catalog, load_signals, data_freshness_note
st.title("Vista d'insieme")

catalog = load_catalog()
signals = load_signals()

datasets = catalog.get("datasets", [])
sig_summary = signals.get("summary", {})
updated_at = catalog.get("updated_at", "?")

n_ok = sig_summary.get("by_status", {}).get("ok", 0)
n_warn = sig_summary.get("by_status", {}).get("warn", 0)
n_err = sig_summary.get("by_status", {}).get("error", 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Dataset", len(datasets))
col2.metric("Pipeline OK", n_ok)
col3.metric("Warning", n_warn)
col4.metric("Errori", n_err)

st.markdown("---")

# Dataset per stage
stage_counts = {}
for ds in datasets:
    s = ds.get("stage", "unknown")
    stage_counts[s] = stage_counts.get(s, 0) + 1

stage_df = pd.DataFrame([
    {"stage": s.capitalize(), "count": c}
    for s, c in sorted(stage_counts.items())
])

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Dataset per stage")
    if not stage_df.empty:
        st.bar_chart(stage_df.set_index("stage"))
    else:
        st.info("Nessun dato stage disponibile.")
    st.caption(f"Catalogo aggiornato: {updated_at}")

with col_b:
    st.subheader("Ultimi 10 dataset")
    for ds in datasets[:10]:
        st.write(f"- **{ds.get('slug', '?')}** · {ds.get('stage', '?')}")

st.markdown("---")

# Dataset per source_id
st.subheader("Dataset per fonte")
src_counts = {}
for ds in datasets:
    src = ds.get("source_id", "altre")
    src_counts[src] = src_counts.get(src, 0) + 1
if src_counts:
    src_df = pd.DataFrame([
        {"fonte": s, "dataset": c}
        for s, c in sorted(src_counts.items(), key=lambda x: -x[1])
    ])
    st.bar_chart(src_df.set_index("fonte"))
else:
    st.info("Nessun dato fonte disponibile.")

data_freshness_note()
