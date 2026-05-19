"""Pipeline Health — stato segnali CI, success rate e distribuzione per fonte."""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_signals, data_freshness_note
st.title("⚙️ Pipeline CI")

signals = load_signals()
sigs = signals.get("signals", [])

ok_count = sum(1 for s in sigs if s.get("status") == "ok")
warn_count = sum(1 for s in sigs if s.get("status") == "warn")
err_count = sum(1 for s in sigs if s.get("status") == "error")

# Success rate run
run_passed = sum(1 for s in sigs if s.get("sample_run", {}).get("status") == "passed")
run_failed = sum(1 for s in sigs if s.get("sample_run", {}).get("status") == "failed")
run_none = len(sigs) - run_passed - run_failed

col1, col2, col3, col4 = st.columns(4)
col1.metric("✅ Segnali OK", ok_count, "configurazione valida")
col2.metric("🏃 Run passati", run_passed, f"{run_passed}/{ok_count} segnali")
col3.metric("❌ Run falliti", run_failed,
            f"{round(run_failed/(run_passed+run_failed)*100)}% dei run" if run_failed else "nessuno")
col4.metric("⏳ Mai eseguiti", run_none, "senza run CI")

if run_failed:
    st.caption(
        "⚠️ **Nota**: i run falliti sono segnali con configurazione valida "
        "ma ultima esecuzione CI andata male (es. fonte irraggiungibile). "
        "Vedi dettaglio sotto per i candidati coinvolti."
    )

st.markdown("---")
st.subheader("Distribuzione per stato run")

col_a, col_b = st.columns([1, 1.5])
with col_a:
    run_df = pd.DataFrame([
        {"stato": "Passati", "count": run_passed},
        {"stato": "Falliti", "count": run_failed},
        {"stato": "Mai eseguiti", "count": run_none},
    ])
    pie = alt.Chart(run_df).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="count", type="quantitative"),
        color=alt.Color(
            field="stato", type="nominal",
            scale={"domain": ["Passati", "Falliti", "Mai eseguiti"],
                   "range": ["#16a34a", "#dc2626", "#94a3b8"]},
        ),
        tooltip=["stato", "count"],
    ).properties(width=300, height=300)
    st.altair_chart(pie)

with col_b:
    # Candidate per fonte
    src_counts = {}
    for s in sigs:
        src = s.get("source_id") or "altre"
        src_counts[src] = src_counts.get(src, 0) + 1
    if src_counts:
        src_df = pd.DataFrame([
            {"fonte": s, "candidati": c}
            for s, c in sorted(src_counts.items(), key=lambda x: -x[1])
        ])
        st.subheader("Candidate per fonte")
        st.bar_chart(src_df.set_index("fonte"))
    else:
        st.info("Nessuna fonte")

st.markdown("---")
st.subheader("Dettaglio ultimo run")

for sig in sigs:
    sr = sig.get("sample_run", {}) or {}
    label = sig.get("label", "?")
    status_emoji = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(
        sig.get("status", ""), "❓"
    )

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
