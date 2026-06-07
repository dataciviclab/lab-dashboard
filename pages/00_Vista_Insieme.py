"""
Vista d'insieme — polso del DataCivicLab.
Metriche e stato da Source Observatory, Dataset Incubator e Community.
"""

import altair as alt
import pandas as pd
import streamlit as st

from sources import (
    data_freshness_note,
    load_catalog,
    load_check_coverage,
    load_inventory_report,
    load_radar,
    load_signals,
    load_sources_registry,
)

st.title("📊 Vista d'insieme")

st.markdown("Salute del Lab: dalle fonti monitorate ai dataset pubblicati.")

# ── Carica tutti i dati ──────────────────────────────────────────
radar = load_radar()
registry = load_sources_registry()
coverage_df = load_check_coverage()
inventory_report = load_inventory_report()
catalog = load_catalog()
pipeline_signals = load_signals()

sources = radar.get("sources", [])
status_counts = radar.get("status_counts", {})
persistent_red = radar.get("persistent_red", 0)
inventory_sources = inventory_report.get("sources", {})
datasets = catalog.get("datasets", [])
sigs = pipeline_signals.get("signals", [])

# Conteggi
n_registry = len(registry)
n_radar = len(sources)
n_green = status_counts.get("GREEN", 0)
n_yellow = status_counts.get("YELLOW", 0)
n_red = status_counts.get("RED", 0)

n_inv_ok = sum(1 for v in inventory_sources.values() if v.get("status") == "ok")

tot_inv = int(coverage_df["inv_items"].sum()) if not coverage_df.empty else 0
tot_chk = int(coverage_df["chk_items"].sum()) if not coverage_df.empty else 0
coverage_pct = round(tot_chk / tot_inv * 100, 1) if tot_inv else 0

n_published = sum(1 for ds in datasets if ds.get("stage") == "published")
n_incubating = sum(1 for ds in datasets if ds.get("stage") == "incubating")
n_pipeline_err = sum(1 for sig in sigs if sig.get("status") == "error")

# ── KPI ──────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("📡 Radar fonti", f"{n_radar}/{n_registry}", f"{n_green}🟢 {n_yellow}🟡 {n_red}🔴")
col2.metric("📦 Items inventario", f"{tot_inv:,}", f"{coverage_pct}% checked ({tot_chk:,})")
col3.metric(
    "📚 Dataset", f"{len(datasets)}", f"{n_published} pubblicati · {n_incubating} in incubazione"
)
col4.metric("✅ Pubblicati", n_published, f"{n_incubating} in incubazione")

if persistent_red:
    st.warning(
        f"🔴 **{persistent_red} fonte/i persistentemente RED** "
        "(streak > 7 giorni) — vedi Radar per dettaglio"
    )

if n_pipeline_err:
    st.error(f"❌ **{n_pipeline_err} pipeline in errore** — vedi Pipeline CI")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SOURCE OBSERVATORY
# ══════════════════════════════════════════════════════════════════
st.subheader("Source Observatory")

# -- Stato radar --
col_s1, col_s2, col_s3 = st.columns([1, 1, 1])

with col_s1:
    st.metric("🟢 GREEN", n_green)
with col_s2:
    st.metric("🟡 YELLOW", n_yellow)
with col_s3:
    st.metric("🔴 RED", n_red)

# Bar chart radar: barra per stato
if n_radar:
    radar_df = pd.DataFrame(
        [
            {"stato": "GREEN", "conteggio": n_green, "colore": "#16a34a"},
            {"stato": "YELLOW", "conteggio": n_yellow, "colore": "#fbbf24"},
            {"stato": "RED", "conteggio": n_red, "colore": "#dc2626"},
        ]
    )
    radar_bars = (
        alt.Chart(radar_df)
        .mark_bar()
        .encode(
            x=alt.X("stato:N", title=None, sort=["GREEN", "YELLOW", "RED"]),
            y=alt.Y("conteggio:Q", title="Fonti"),
            color=alt.Color(
                "stato:N",
                scale={
                    "domain": ["GREEN", "YELLOW", "RED"],
                    "range": ["#16a34a", "#fbbf24", "#dc2626"],
                },
                title=None,
                legend=None,
            ),
            tooltip=["stato:N", "conteggio:Q"],
        )
        .properties(height=150)
    )
    st.altair_chart(radar_bars, use_container_width=True)


st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# DATASET
# ══════════════════════════════════════════════════════════════════
st.subheader("Dataset")

stages = sorted(set(d.get("stage", "unknown") for d in datasets))
stage_filter = st.selectbox("Filtra per stage", ["Tutti"] + stages)

search = st.text_input("Cerca dataset", placeholder="slug, nome o descrizione...")

filtered = datasets
if stage_filter != "Tutti":
    filtered = [d for d in filtered if d.get("stage") == stage_filter]
if search:
    q = search.lower()
    filtered = [
        d
        for d in filtered
        if q in d.get("slug", "").lower()
        or q in d.get("name", "").lower()
        or q in d.get("description", "").lower()
    ]

st.write(f"**{len(filtered)} dataset** trovati")

for ds in filtered:
    period = ds.get("period", {})
    yrs = f"{period.get('start', '?')}–{period.get('end', '?')}" if period else "?"
    with st.expander(f"**{ds.get('slug', '?')}** — {ds.get('stage', '?')}"):
        st.write(f"**Nome:** {ds.get('name', '—')}")
        st.write(f"**Descrizione:** {ds.get('description', '—')}")
        st.write(f"**Fonte:** {ds.get('source', '?')}")
        st.write(f"**Anni:** {yrs}")
        loc = ds.get("location", {})
        if loc.get("path"):
            st.write(f"**Path GCS:** `{loc['path']}`")

        # Schema colonne
        cols = ds.get("columns", [])
        if cols:
            st.markdown("**Schema colonne**")
            col_df = pd.DataFrame(
                [
                    {
                        "colonna": c.get("name", "?"),
                        "tipo": c.get("type", "?"),
                        "ruolo": c.get("role", "?"),
                        "descrizione": c.get("description", ""),
                    }
                    for c in cols
                ]
            )
            st.dataframe(col_df, hide_index=True, use_container_width=True)

# -- Alert run falliti --
run_failed = [s for s in sigs if s.get("sample_run", {}).get("status") == "failed"]
if run_failed:
    st.warning(
        f"⚠️ **{len(run_failed)} candidate con run CI fallito** "
        f"— vai a ⚙️ Pipeline candidate per dettagli"
    )

if n_pipeline_err:
    st.warning(f"⚠️ **{n_pipeline_err} pipeline in errore**")

data_freshness_note()
