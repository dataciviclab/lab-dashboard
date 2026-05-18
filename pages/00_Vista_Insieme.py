"""Vista d'insieme — metriche aggregate."""
import streamlit as st
import pandas as pd
from sources import load_catalog, load_signals, render_sidebar_common
render_sidebar_common()

st.title("Vista d'insieme")

catalog = load_catalog()
signals = load_signals()

datasets = catalog.get("datasets", [])
sigs = signals.get("signals", [])
sig_summary = signals.get("summary", {})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Dataset", len(datasets))
col2.metric("Pipeline OK", sig_summary.get("by_status", {}).get("ok", 0))
col3.metric("Warning", sig_summary.get("by_status", {}).get("warn", 0))
col4.metric("Errori", sig_summary.get("by_status", {}).get("error", 0))

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
    st.bar_chart(stage_df.set_index("stage"))
    st.caption(f"Ultimo aggiornamento: {catalog.get('updated_at', '?')}")

with col_b:
    st.subheader("Ultimi aggiornamenti")
    recent = sorted(
        datasets, key=lambda d: d.get("updated_at", ""), reverse=True
    )[:10]
    for ds in recent:
        st.write(f"- **{ds.get('slug', '?')}** · {ds.get('stage', '?')}")

st.markdown("---")

# Dataset per tema
st.subheader("Dataset per tema")
theme_counts = {}
for ds in datasets:
    for t in ds.get("themes", []):
        theme_counts[t] = theme_counts.get(t, 0) + 1
if theme_counts:
    theme_df = pd.DataFrame([
        {"tema": t, "count": c}
        for t, c in sorted(theme_counts.items(), key=lambda x: -x[1])
    ])
    st.bar_chart(theme_df.set_index("tema"))
