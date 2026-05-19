"""Pipeline Health — stato segnali CI con dettaglio ultimo run."""
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
        label = sig.get("label", "?")
        st.write(f"{emoji} **{label}** — {sig.get('detail', '')}")

st.markdown("---")
st.subheader("Dettaglio ultimo run")

for sig in sigs:
    sr = sig.get("sample_run", {}) or {}
    label = sig.get("label", "?")
    status_emoji = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(
        sig.get("status", ""), "❓"
    )

    # Badge run status
    run_status = sr.get("status", "")
    run_badge = {"passed": "✅ passato", "failed": "❌ fallito"}.get(
        run_status, "⚪ sconosciuto"
    )

    checked_at = sr.get("checked_at", "")
    run_url = sr.get("run_url", "")
    run_year = sr.get("year", "")

    with st.expander(f"{status_emoji} **{label}** — run: {run_badge}"):
        st.write(f"**Dettaglio segnale:** {sig.get('detail', '')}")
        if checked_at:
            st.write(f"**Ultimo check:** {checked_at}")
        if run_year:
            st.write(f"**Anno testato:** {run_year}")
        if run_url:
            st.write(f"**Run CI:** [{run_url}]({run_url})")
        st.write(f"**Source ID:** {sig.get('source_id', '?')}")

data_freshness_note()
