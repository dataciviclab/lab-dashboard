"""Registry / Repo — stato dei registry di ogni repo del Lab."""

import pandas as pd
import streamlit as st

from sources import data_freshness_note, load_operational_topics, load_workspace_triage

st.title("📦 Registry / Repo")
st.markdown(
    "Stato dei registry di ogni repo del Lab: dataset, mart, segnali pipeline e salute complessiva."
)

# ── Carica dati ─────────────────────────────────────────────────
triage = load_workspace_triage()
registry_summary = triage.get("registry_summary", [])

# Separa repo attivi da non-attivi
active = [r for r in registry_summary if r.get("available")]
inactive = [r for r in registry_summary if not r.get("available")]

# ── KPI aggregati ───────────────────────────────────────────────
tot_ds = sum(r.get("datasets", 0) for r in active)
tot_marts = sum(r.get("marts", 0) for r in active)
tot_signals = sum(r.get("signals", 0) for r in active)
tot_gcs = sum(r.get("gcs", 0) for r in active)

st.subheader("Panoramica")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Repo con registry", f"{len(active)}", f"{len(inactive)} senza registry")
col2.metric("📚 Dataset totali", f"{tot_ds}")
col3.metric("📊 Mart totali", f"{tot_marts}")
col4.metric("📡 Segnali totali", f"{tot_signals}")

st.markdown("---")

# ── Tabella repo ────────────────────────────────────────────────
st.subheader("Dettaglio repo")

rows = []
for r in active:
    sigs = r.get("signals_detail", [])
    ok = sum(1 for s in sigs if s.get("status") == "ok")
    warn = sum(1 for s in sigs if s.get("status") == "warn")
    error = sum(1 for s in sigs if s.get("status") == "error")
    rows.append(
        {
            "repo": r["repo"],
            "source_repo": r.get("source_repo", ""),
            "datasets": r.get("datasets", 0),
            "marts": r.get("marts", 0),
            "signals": r.get("signals", 0),
            "gcs": r.get("gcs", 0),
            "ok": ok,
            "warn": warn,
            "error": error,
            "updated_at": r.get("updated_at", ""),
        }
    )

df = pd.DataFrame(rows)

if not df.empty:
    st.dataframe(
        df,
        column_config={
            "repo": st.column_config.TextColumn("Repo", width="medium"),
            "source_repo": st.column_config.TextColumn("Source repo", width="medium"),
            "datasets": st.column_config.NumberColumn("Dataset", format="%d"),
            "marts": st.column_config.NumberColumn("Mart", format="%d"),
            "signals": st.column_config.NumberColumn("Segnali", format="%d"),
            "gcs": st.column_config.NumberColumn("GCS", format="%d"),
            "ok": st.column_config.NumberColumn("✅", format="%d"),
            "warn": st.column_config.NumberColumn("⚠️", format="%d"),
            "error": st.column_config.NumberColumn("❌", format="%d"),
            "updated_at": st.column_config.TextColumn("Aggiornato", width="small"),
        },
        hide_index=True,
        width="stretch",
    )

    # Grafico a barre: dataset per repo
    chart_df = df[["repo", "datasets"]].sort_values("datasets", ascending=False)
    if not chart_df.empty:
        st.subheader("Dataset per repo")
        import altair as alt

        chart = (
            alt.Chart(chart_df)
            .mark_bar(color="#3b82f6")
            .encode(
                y=alt.Y("repo:N", title=None, sort="-x"),
                x=alt.X("datasets:Q", title="Dataset"),
                tooltip=["repo", "datasets"],
            )
            .properties(height=max(25 * len(chart_df), 100))
        )
        st.altair_chart(chart, width="stretch")
else:
    st.info("Nessun registry disponibile.")

# ── Repo senza registry ─────────────────────────────────────────
if inactive:
    st.markdown("---")
    st.subheader("Repo senza registry")
    st.caption("Questi repo non hanno ancora un registry.json migrato.")
    for r in inactive:
        st.write(f"- **{r['repo']}** — {r.get('reason', 'registry_not_found')}")

# ── Temi operativi (topic_index.operational_topics) ──────────────
topics = load_operational_topics()
if topics:
    st.markdown("---")
    st.subheader("Temi operativi")
    cols = st.columns(len(topics))
    for col, (key, t) in zip(cols, topics.items()):
        with col:
            st.markdown(f"**{key.title()}**")
            st.caption(t.get("summary", ""))
            if t.get("repos"):
                st.caption("Repo: " + ", ".join(t["repos"]))
            if t.get("next"):
                st.caption(f"→ {t['next']}")

st.markdown("---")
st.caption(
    "Dati: ACB (workspace_triage.json → registry_summary, topic_index.json → operational_topics)"
)
data_freshness_note()
