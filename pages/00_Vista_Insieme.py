"""Vista d'insieme — polso del DataCivicLab."""

import altair as alt
import pandas as pd
import streamlit as st

from sources import (
    data_freshness_note,
    load_catalog,
    load_radar,
    load_signals,
    load_workspace_triage,
)

st.title("📊 Vista d'insieme")

# ── Carica dati ─────────────────────────────────────────────────
triage = load_workspace_triage()
radar = load_radar()
catalog = load_catalog()
signals_data = load_signals()

sources = radar.get("sources", [])
status_counts = radar.get("status_counts", {})
persistent_red = radar.get("persistent_red", 0)
datasets = catalog.get("datasets", [])
sigs = signals_data.get("signals", [])

prs = triage.get("prs", [])
issues = triage.get("issues", [])
discussions = triage.get("discussions", [])

# Conteggi
tot = len(datasets)
published = sum(1 for d in datasets if d.get("stage") == "published")
incubating = tot - published
n_green = status_counts.get("GREEN", 0)
n_yellow = status_counts.get("YELLOW", 0)
n_red = status_counts.get("RED", 0)
ok_count = sum(1 for s in sigs if s.get("status") == "ok")
warn_count = sum(1 for s in sigs if s.get("status") == "warn")
error_count = sum(1 for s in sigs if s.get("status") == "error")

# ══════════════════════════════════════════════════════════════════
# KPI COMPATTA
# ══════════════════════════════════════════════════════════════════
col1, col2, col3, col4 = st.columns(4)
col1.metric("📡 Radar", f"{n_green + n_yellow + n_red}", f"{n_green}🟢 {n_yellow}🟡 {n_red}🔴")
col2.metric("📚 Dataset", f"{tot}", f"{published} pubblicati")
col3.metric("⚡ Pipeline", f"{ok_count}", f"{warn_count}⚠️ {error_count}❌")
col4.metric("🔀 PR", len(prs), f"{len(issues)} issues · {len(discussions)} disc")

if persistent_red:
    st.warning(f"🔴 **{persistent_red} fonte/i RED persistente** (streak > 7gg)")
if error_count:
    st.error(f"❌ **{error_count} pipeline in errore**")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# RADAR — barra segmentata
# ══════════════════════════════════════════════════════════════════
st.subheader("Radar fonti")

radar_df = pd.DataFrame(
    [
        {"stato": "GREEN", "n": n_green},
        {"stato": "YELLOW", "n": n_yellow},
        {"stato": "RED", "n": n_red},
    ]
)
radar_df = radar_df[radar_df["n"] > 0]  # nascondi zero

if not radar_df.empty:
    chart = (
        alt.Chart(radar_df)
        .mark_bar(height=30)
        .encode(
            x=alt.X("n:Q", stack="normalize", title=None, axis=None),
            color=alt.Color(
                "stato:N",
                scale={
                    "domain": ["GREEN", "YELLOW", "RED"],
                    "range": ["#16a34a", "#fbbf24", "#dc2626"],
                },
                legend=None,
            ),
            tooltip=["stato", "n"],
        )
        .properties(height=30)
    )
    st.altair_chart(chart, width="stretch")
    # Legenda manuale
    parts = []
    if n_green:
        parts.append(f"🟢 {n_green}")
    if n_yellow:
        parts.append(f"🟡 {n_yellow}")
    if n_red:
        parts.append(f"🔴 {n_red}")
    st.caption(f"{' · '.join(parts)} — {len(sources)} fonti totali")

# ── Fonti RED non healthy ───────────────────────────────────────
unhealthy = [s for s in sources if s.get("status") in ("YELLOW", "RED")]
if unhealthy:
    with st.expander(f"⚠️ {len(unhealthy)} fonti non healthy", expanded=False):
        for s in unhealthy:
            icon = "🔴" if s.get("status") == "RED" else "🟡"
            streak = s.get("red_streak", 0)
            st.write(
                f"{icon} **{s['id']}** — {s.get('note', '')}{' (streak ' + str(streak) + ')' if streak else ''}"
            )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# DATASET PER FONTE
# ══════════════════════════════════════════════════════════════════
st.subheader("Dataset per fonte")

by_source: dict[str, list[dict]] = {}
for ds in datasets:
    sid = ds.get("source_id") or ds.get("source", "unknown")
    by_source.setdefault(sid, []).append(ds)

# Top 15 fonti
top = sorted(by_source.items(), key=lambda x: -len(x[1]))[:15]
chart_df = pd.DataFrame([{"fonte": s[:30], "n": len(ds)} for s, ds in top])

if not chart_df.empty:
    chart = (
        alt.Chart(chart_df)
        .mark_bar(color="#3b82f6")
        .encode(
            y=alt.Y("fonte:N", title=None, sort="-x"),
            x=alt.X("n:Q", title="Dataset"),
            tooltip=["fonte", "n"],
        )
        .properties(height=max(22 * len(chart_df), 80))
    )
    st.altair_chart(chart, width="stretch")

# Tabella compatta fonti
st.write(f"**{len(by_source)} fonti** · {tot} dataset totali")
table_rows = []
for s, ds in top:
    pub = sum(1 for d in ds if d.get("stage") == "published")
    inc = sum(1 for d in ds if d.get("stage") == "incubating")
    stage_str = "+".join(filter(None, [f"{pub}pub" if pub else "", f"{inc}inc" if inc else ""]))
    table_rows.append({"fonte": s, "n": len(ds), "stage": stage_str})

if table_rows:
    df_table = pd.DataFrame(table_rows)
    st.dataframe(
        df_table,
        column_config={
            "fonte": "Fonte",
            "n": st.column_config.NumberColumn("Dataset", format="%d"),
            "stage": "Stage",
        },
        hide_index=True,
        width="stretch",
        height=min(35 * len(table_rows) + 35, 300),
    )

data_freshness_note()
