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
    load_sources_dashboard,
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

# Data ISO → leggibile (es. 2026-08-06 06:03 UTC)
if generated_at:
    try:
        probe_time = pd.to_datetime(generated_at).strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        probe_time = generated_at
else:
    probe_time = "?"

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
col3.metric(
    "📦 Inventario OK",
    f"{n_inventory_ok}/{n_inventory}",
    f"{n_inventory_err} errori" if n_inventory_err else "nessun errore",
)
col4.metric("📡 Radar attivi", n_radar, None)

if radar.get("persistent_red", 0):
    st.warning(f"🔴 **{radar['persistent_red']} fonte/i** persistentemente RED (streak > 7 giorni)")

st.caption(f"Ultimo probe radar: {probe_time} UTC · inventory: {n_inventory} fonti")
st.markdown("---")

# ── Attenzioni operative ───────────────────────────────────────────
st.subheader("🔎 Attenzioni operative")

so_dash = load_sources_dashboard()
dash_list = so_dash.get("sources", [])

ssl_issues = [s for s in sources if s.get("ssl_issue")]
red_sources = [s for s in sources if (s.get("red_streak") or 0) > 0]
inventory_changed = [d for d in dash_list if d.get("verdict") == "INVENTORY_CHANGED"]
low_readiness = [d for d in dash_list if (d.get("avg_readiness") or 10) < 4]

attenzioni = []
if ssl_issues:
    dettaglio = ", ".join(f"`{s['id']}` (streak {s.get('ssl_streak')}g)" for s in ssl_issues)
    attenzioni.append(f"🔒 **SSL fallback**: {dettaglio}")
if red_sources:
    dettaglio = ", ".join(f"`{s['id']}`" for s in red_sources)
    attenzioni.append(f"🔴 **RED streak**: {dettaglio}")
if inventory_changed:
    dettaglio = ", ".join(f"`{d['source_id']}`" for d in inventory_changed[:8])
    extra = f" (+{len(inventory_changed) - 8})" if len(inventory_changed) > 8 else ""
    attenzioni.append(f"🔄 **Inventario cambiato**: {dettaglio}{extra}")
if low_readiness:
    dettaglio = ", ".join(
        f"`{d['source_id']}` ({d.get('avg_readiness'):g})" for d in low_readiness[:8]
    )
    extra = f" (+{len(low_readiness) - 8})" if len(low_readiness) > 8 else ""
    attenzioni.append(f"🔴 **Readiness bassa (<4)**: {dettaglio}{extra}")

if attenzioni:
    for a in attenzioni:
        st.markdown(f"- {a}")
    st.caption(
        "Dettaglio per fonte: **🔍 Scheda fonte** (menu Source Observatory). "
        "Readiness: da sources_dashboard (report v2)."
    )
else:
    st.success("Nessuna attenzione operativa rilevata.")

st.markdown("---")

# ── Radar trend ───────────────────────────────────────────────────
st.subheader("Trend radar storico")

probes = radar_history_data.get("probes", [])

if probes:
    rows = []
    for probe in probes:
        pdate = probe.get("probe_date", "?")
        for src in probe.get("sources", []):
            rows.append(
                {
                    "data": pdate,
                    "fonte": src.get("id", "?"),
                    "stato": src.get("status", "?"),
                }
            )

    if rows:
        hist_df = pd.DataFrame(rows)
        # Deduplica: più probe nella stessa data gonfiano i conteggi
        hist_df = hist_df.drop_duplicates(subset=["data", "fonte"], keep="last")

        # 1. Line chart: conteggi per stato nel tempo
        trend = hist_df.groupby(["data", "stato"]).size().reset_index(name="conteggio")
        status_order = ["GREEN", "YELLOW", "RED"]
        trend["stato"] = pd.Categorical(trend["stato"], categories=status_order, ordered=True)
        trend = trend.sort_values(["data", "stato"])

        line_chart = (
            alt.Chart(trend)
            .mark_line(point=True)
            .encode(
                x=alt.X("data:T", title="Data"),
                y=alt.Y("conteggio:Q", title="Fonti"),
                color=alt.Color(
                    "stato:N",
                    scale={
                        "domain": ["GREEN", "YELLOW", "RED"],
                        "range": ["#16a34a", "#fbbf24", "#dc2626"],
                    },
                    title="Stato",
                ),
                tooltip=["data:T", "stato:N", "conteggio:Q"],
            )
            .properties(height=220)
        )
        st.altair_chart(line_chart, width="stretch")

        # 2. Heatmap fonte × data — solo fonti con almeno uno stato non-GREEN
        non_green = sorted(hist_df.loc[hist_df["stato"] != "GREEN", "fonte"].unique())
        if non_green:
            heat_df = hist_df[hist_df["fonte"].isin(non_green)]

            # Ordinate per stato più recente
            latest_date = heat_df["data"].max()
            latest_status = (
                heat_df[heat_df["data"] == latest_date]
                .groupby("fonte")["stato"]
                .first()
                .reset_index()
            )
            status_rank = {"RED": 0, "YELLOW": 1, "GREEN": 2}
            latest_status["ordine"] = latest_status["stato"].map(status_rank).fillna(3)
            fonte_order = latest_status.sort_values("ordine")["fonte"].tolist()

            heat = (
                alt.Chart(heat_df)
                .mark_rect()
                .encode(
                    x=alt.X("data:O", title="Data", axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y("fonte:N", title="Fonte", sort=fonte_order),
                    color=alt.Color(
                        "stato:N",
                        scale={
                            "domain": ["GREEN", "YELLOW", "RED", "?"],
                            "range": ["#16a34a", "#fbbf24", "#dc2626", "#94a3b8"],
                        },
                        title="Stato",
                    ),
                    tooltip=["data:O", "fonte:N", "stato:N"],
                )
                .properties(height=320)
            )
            st.altair_chart(heat, width="stretch")
            st.caption(
                f"Heatmap limitata alle {len(non_green)} fonti con stati non-GREEN nel periodo."
            )
        else:
            st.info("Nessuna fonte ha avuto stati non-GREEN nel periodo osservato.")
    else:
        st.info("Nessun dato storico disponibile.")
else:
    st.info("Storico probe non ancora disponibile.")

data_freshness_note()
