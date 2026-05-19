"""
Radar — salute e trend del monitoraggio fonti.
Funnel delle fonti, stato radar GREEN/YELLOW/RED, trend storico.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import (
    load_radar, load_radar_history, load_sources_registry,
    load_inventory_report, load_catalog_signals, load_signals,
    data_freshness_note,
)
st.title("📡 Radar")

st.markdown(
    "Stato del monitoraggio delle fonti pubbliche: "
    "dalla scoperta all'intake. "
    "Il funnel mostra quante fonti arrivano a ogni stadio."
)

# ── Carica dati ───────────────────────────────────────────────────
radar = load_radar()
radar_history_data = load_radar_history()
registry = load_sources_registry()
inventory_report = load_inventory_report()
catalog_signals = load_catalog_signals()
pipeline_signals = load_signals()

sources = radar.get("sources", [])
status_counts = radar.get("status_counts", {})
generated_at = radar.get("generated_at", "")
inventory_sources = inventory_report.get("sources", {})
signals_list = catalog_signals.get("signals", [])
sigs = pipeline_signals.get("signals", [])

radar_map = {s["id"]: s for s in sources}
signals_map = {sig.get("source", ""): sig for sig in signals_list}

candidate_source_ids = set()
for sig in sigs:
    if sig.get("source_id"):
        candidate_source_ids.add(sig["source_id"])

# ── Funnel SO ─────────────────────────────────────────────────────
st.subheader("Funnel")

n_registry = len(registry)
n_radar = len(sources)
n_green = status_counts.get("GREEN", 0)
n_yellow = status_counts.get("YELLOW", 0)
n_red = status_counts.get("RED", 0)
n_inventory = len(inventory_sources)
n_inventory_ok = sum(1 for v in inventory_sources.values() if v.get("status") == "ok")
n_inventory_err = sum(1 for v in inventory_sources.values() if v.get("status") == "error")
n_signaled = sum(1 for sig in signals_map.values()
                 if sig.get("suggested_action") == "catalog-watch-ready")
n_candidate = len(candidate_source_ids)

max_n = max(n_registry, n_radar, n_inventory, n_signaled, n_candidate, 1)

stages_info = [
    ("📋 Registro fonti", n_registry, "#94a3b8"),
    ("📡 Radar", n_radar, "#3b82f6"),
    ("📦 Inventario", n_inventory, "#f59e0b"),
    ("🎯 Pronto intake", n_signaled, "#8b5cf6"),
    ("📥 Candidate SO→DI", n_candidate, "#16a34a"),
]

for label, count, color in stages_info:
    pct = count / max_n
    cols = st.columns([2.5, 12])
    with cols[0]:
        st.write(f"**{label}**")
    with cols[1]:
        bar_html = f"""
        <div style="border-radius:8px; height:32px; overflow:hidden;">
            <div style="background:{color}; width:{pct*100:.0f}%; height:100%;
                border-radius:8px; display:flex; align-items:center; padding-left:10px;">
                <span style="font-weight:bold; font-size:16px;">{count}</span>
            </div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)

st.markdown("---")

# ── Metriche ──────────────────────────────────────────────────────
st.subheader("Indicatori")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Totale fonti", n_registry, f"{n_radar} monitorate")
col2.metric("🟢 GREEN", n_green, f"{n_yellow} YELLOW · {n_red} RED")
col3.metric("📦 Inventario OK", f"{n_inventory_ok}/{n_inventory}",
            f"{n_inventory_err} errori" if n_inventory_err else "nessun errore")
col4.metric("🎯 Pronto intake", n_signaled, f"{n_candidate} candidate")

if radar.get("persistent_red", 0):
    st.warning(f"🔴 **{radar['persistent_red']} fonte/i** "
               f"persistentemente RED (streak > 7 giorni)")

st.caption(f"Ultimo probe radar: {generated_at} · "
           f"inventory: {n_inventory} fonti")
st.markdown("---")

# ── Radar trend ───────────────────────────────────────────────────
st.subheader("Trend radar storico")

probes = radar_history_data.get("probes", [])

if probes:
    rows = []
    for probe in probes:
        pdate = probe.get("probe_date", "?")
        for src in probe.get("sources", []):
            rows.append({
                "data": pdate,
                "fonte": src.get("id", "?"),
                "stato": src.get("status", "?"),
            })

    if rows:
        hist_df = pd.DataFrame(rows)
        # Deduplica: più probe nella stessa data gonfiano i conteggi
        hist_df = hist_df.drop_duplicates(subset=["data", "fonte"], keep="last")

        # 1. Line chart: conteggi per stato nel tempo
        trend = (hist_df.groupby(["data", "stato"])
                 .size().reset_index(name="conteggio"))
        status_order = ["GREEN", "YELLOW", "RED"]
        trend["stato"] = pd.Categorical(
            trend["stato"], categories=status_order, ordered=True)
        trend = trend.sort_values(["data", "stato"])

        line_chart = alt.Chart(trend).mark_line(point=True).encode(
            x=alt.X("data:T", title="Data"),
            y=alt.Y("conteggio:Q", title="Fonti"),
            color=alt.Color(
                "stato:N",
                scale={"domain": ["GREEN", "YELLOW", "RED"],
                       "range": ["#16a34a", "#fbbf24", "#dc2626"]},
                title="Stato",
            ),
            tooltip=["data:T", "stato:N", "conteggio:Q"],
        ).properties(height=220)
        st.altair_chart(line_chart, use_container_width=True)

        # 2. Heatmap fonte × data — ordinate per stato più recente
        latest_date = hist_df["data"].max()
        latest_status = (
            hist_df[hist_df["data"] == latest_date]
            .groupby("fonte")["stato"].first().reset_index()
        )
        status_rank = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        latest_status["ordine"] = (
            latest_status["stato"].map(status_rank).fillna(3))
        fonte_order = latest_status.sort_values("ordine")["fonte"].tolist()

        heat = alt.Chart(hist_df).mark_rect().encode(
            x=alt.X("data:O", title="Data", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("fonte:N", title="Fonte", sort=fonte_order),
            color=alt.Color(
                "stato:N",
                scale={"domain": ["GREEN", "YELLOW", "RED", "?"],
                       "range": ["#16a34a", "#fbbf24", "#dc2626", "#94a3b8"]},
                title="Stato",
            ),
            tooltip=["data:O", "fonte:N", "stato:N"],
        ).properties(height=320)
        st.altair_chart(heat, use_container_width=True)
    else:
        st.info("Nessun dato storico disponibile.")
else:
    st.info("Storico probe non ancora disponibile.")

data_freshness_note()
