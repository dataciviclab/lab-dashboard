"""Pipeline Health — stato segnali CI."""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_signals, render_sidebar_common, data_freshness_note
render_sidebar_common()

st.title("Pipeline Health")

signals = load_signals()
sigs = signals.get("signals", [])

ok_count = sum(1 for s in sigs if s.get("status") == "ok")
warn_count = sum(1 for s in sigs if s.get("status") == "warn")
err_count = sum(1 for s in sigs if s.get("status") == "error")

col1, col2, col3 = st.columns(3)
col1.metric("✅ OK", ok_count)
col2.metric("⚠️ Warning", warn_count)
col3.metric("❌ Errori", err_count)

st.markdown("---")
st.subheader("Distribuzione")

col_a, col_b = st.columns([1, 2])
with col_a:
    status_df = pd.DataFrame([
        {"status": "OK", "count": ok_count},
        {"status": "Warning", "count": warn_count},
        {"status": "Error", "count": err_count},
    ])
    pie = alt.Chart(status_df).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="count", type="quantitative"),
        color=alt.Color(
            field="status",
            type="nominal",
            scale={
                "domain": ["OK", "Warning", "Error"],
                "range": ["#16a34a", "#fbbf24", "#dc2626"],
            },
        ),
        tooltip=["status", "count"],
    ).properties(width=300, height=300)
    st.altair_chart(pie)

with col_b:
    st.subheader("Segnali")
    for sig in sigs:
        emoji = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(
            sig.get("status", ""), "❓"
        )
        st.write(f"{emoji} **{sig.get('label', '?')}** — {sig.get('detail', '')}")

data_freshness_note()
