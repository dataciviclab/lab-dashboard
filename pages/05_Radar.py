"""
Radar — salute e trend del monitoraggio fonti.
Segnali radar GREEN/YELLOW/RED, trend storico, indicatori di salute.
"""
import altair as alt
import pandas as pd
import streamlit as st

from sources import (
    data_freshness_note,
    load_inventory_report,
    load_radar,
    load_radar_history,
    load_sources_registry,
)

st.title("📡 Radar")

st.markdown(
    "Salute delle fonti monitorate dal Source Observatory: "
    "stato radar (GREEN/YELLOW/RED) e trend storico dei probe."
)

# ── Carica dati ───────────────────────────────────────────────────
radar = load_radar()
radar_history_data = load_radar_history()
registry = load_sources_registry()
inventory_report = load_inventory_report()

sources = radar.get("sources", [])
status_counts = radar.get("status_counts", {})
generated_at = radar.get("generated_at", "")
inventory_sources = inventory_report.get("sources", {})

# ── Metriche ──────────────────────────────────────────────────────
st.subheader("Indicatori")

n_registry = len(registry)
n_radar = len(sources)
n_green = status_counts.get("GREEN", 0)
n_yellow = status_counts.get("YELLOW", 0)
n_red = status_counts.get("RED", 0)
n_inventory = len(inventory_sources)
n_inventory_ok = sum(1 for v in inventory_sources.values() if v.get("status") == "ok")
n_inventory_err = sum(1 for v in inventory_sources.values() if v.get("status") == "error")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Totale fonti", n_registry, f"{n_radar} monitorate")
col2.metric("🟢 GREEN", n_green, f"{n_yellow} YELLOW · {n_red} RED")
col3.metric("📦 Inventario OK", f"{n_inventory_ok}/{n_inventory}",
            f"{n_inventory_err} errori" if n_inventory_err else "nessun errore")
col4.metric("📡 Radar attivi", n_radar, None)

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
