"""
Vista d'insieme — polso del DataCivicLab.
Metriche e stato da Source Observatory, Dataset Incubator e Community.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import (
    load_radar, load_sources_registry, load_check_coverage,
    load_inventory_report, load_catalog_signals,
    load_catalog, load_signals,
    load_discussion_counts,
    data_freshness_note,
)
st.title("DataCivicLab · Dashboard")

st.markdown(
    "Salute del Lab: dalle fonti monitorate ai dataset pubblicati. "
    "I dati sono aggiornati ogni 5 minuti."
)

# ── Carica tutti i dati ──────────────────────────────────────────
radar = load_radar()
registry = load_sources_registry()
coverage_df = load_check_coverage()
inventory_report = load_inventory_report()
catalog_signals = load_catalog_signals()
catalog = load_catalog()
pipeline_signals = load_signals()
disc_counts = load_discussion_counts()

sources = radar.get("sources", [])
status_counts = radar.get("status_counts", {})
persistent_red = radar.get("persistent_red", 0)
inventory_sources = inventory_report.get("sources", {})
signals_map = {sig.get("source", ""): sig for sig in catalog_signals.get("signals", [])}
datasets = catalog.get("datasets", [])
sigs = pipeline_signals.get("signals", [])

# Conteggi
n_registry = len(registry)
n_radar = len(sources)
n_green = status_counts.get("GREEN", 0)
n_yellow = status_counts.get("YELLOW", 0)
n_red = status_counts.get("RED", 0)

n_inv_ok = sum(1 for v in inventory_sources.values() if v.get("status") == "ok")
n_inv_err = sum(1 for v in inventory_sources.values() if v.get("status") == "error")

tot_inv = int(coverage_df["inv_items"].sum()) if not coverage_df.empty else 0
tot_chk = int(coverage_df["chk_items"].sum()) if not coverage_df.empty else 0
coverage_pct = round(tot_chk / tot_inv * 100, 1) if tot_inv else 0

n_published = sum(1 for ds in datasets if ds.get("stage") == "published")
n_incubating = sum(1 for ds in datasets if ds.get("stage") == "incubating")
n_pipeline_err = sum(1 for sig in sigs if sig.get("status") == "error")

n_disc = disc_counts.get("totale", 0)

# ── KPI ──────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("📡 Radar fonti", f"{n_radar}/{n_registry}",
            f"{n_green}🟢 {n_yellow}🟡 {n_red}🔴")
col2.metric("📦 Items inventario", f"{tot_inv:,}",
            f"{coverage_pct}% checked ({tot_chk:,})")
col3.metric("📚 Dataset", f"{len(datasets)}",
            f"{n_published} pubblicati · {n_incubating} in incubazione")
col4.metric("💬 Discussioni", n_disc)

if persistent_red:
    st.warning(f"🔴 **{persistent_red} fonte/i persistentemente RED** "
               "(streak > 7 giorni) — vedi Radar per dettaglio")

if n_pipeline_err:
    st.error(f"❌ **{n_pipeline_err} pipeline in errore** — vedi Pipeline CI")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# 📡 SOURCE OBSERVATORY
# ══════════════════════════════════════════════════════════════════
st.subheader("📡 Source Observatory")

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
    radar_df = pd.DataFrame([
        {"stato": "GREEN", "conteggio": n_green, "colore": "#16a34a"},
        {"stato": "YELLOW", "conteggio": n_yellow, "colore": "#fbbf24"},
        {"stato": "RED", "conteggio": n_red, "colore": "#dc2626"},
    ])
    radar_bars = alt.Chart(radar_df).mark_bar().encode(
        x=alt.X("stato:N", title=None, sort=["GREEN", "YELLOW", "RED"]),
        y=alt.Y("conteggio:Q", title="Fonti"),
        color=alt.Color(
            "stato:N",
            scale={"domain": ["GREEN", "YELLOW", "RED"],
                   "range": ["#16a34a", "#fbbf24", "#dc2626"]},
            title=None,
            legend=None,
        ),
        tooltip=["stato:N", "conteggio:Q"],
    ).properties(height=150)
    st.altair_chart(radar_bars, use_container_width=True)

# -- Fonti problematiche --
st.markdown("**Fonti con criticità**")

problematic = []
for s in sources:
    if s.get("status") in ("RED", "YELLOW"):
        streak = s.get("red_streak") or 0
        note = s.get("note", "") or ""
        problematic.append({
            "fonte": s["id"],
            "stato": s["status"],
            "http": s.get("http_code", ""),
            "streak": f"{streak}g" if streak else "",
            "nota": note[:80] if note else "",
        })

if problematic:
    st.dataframe(
        pd.DataFrame(problematic),
        column_config={
            "fonte": "Fonte",
            "stato": "Stato",
            "http": "HTTP",
            "streak": "Streak",
            "nota": "Nota",
        },
        hide_index=True,
        use_container_width=True,
        height=min(35 * len(problematic) + 35, 250),
    )
else:
    st.info("Nessuna criticità — tutte le fonti sono GREEN.")

# -- Copertura source check (mini) --
st.markdown("**Copertura source check**")

if not coverage_df.empty:
    cov_col1, cov_col2, cov_col3, cov_col4 = st.columns(4)
    cov_col1.metric("Items inventario", f"{tot_inv:,}")
    cov_col2.metric("Items checked", f"{tot_chk:,}", f"{coverage_pct}%")
    cov_col3.metric("Raggiungibili",
                    f"{int(coverage_df['reachable'].sum()):,}",
                    f"{round(int(coverage_df['reachable'].sum())/tot_chk*100,1) if tot_chk else 0}%")
    cov_col4.metric("Intake candidate",
                    f"{int(coverage_df['candidates'].sum()):,}",
                    f"{round(int(coverage_df['candidates'].sum())/tot_chk*100,1) if tot_chk else 0}%")
else:
    st.info("Dati copertura non disponibili.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# 📚 DATASET INCUBATOR
# ══════════════════════════════════════════════════════════════════
st.subheader("📚 Dataset Incubator")

st.markdown(
    f"**{len(datasets)} dataset** ({n_published} pubblicati, "
    f"{n_incubating} in incubazione) — "
    f"il funnel completo è in **📥 Funnel candidate**."
)

# -- Dataset per stage --
col_d1, col_d2 = st.columns(2)

with col_d1:
    st.subheader("Dataset per stage")
    stage_counts = {}
    for ds in datasets:
        s = ds.get("stage", "unknown")
        stage_counts[s] = stage_counts.get(s, 0) + 1
    stage_df = pd.DataFrame([
        {"stage": s.capitalize(), "count": c}
        for s, c in sorted(stage_counts.items())
    ])
    if not stage_df.empty:
        st.bar_chart(stage_df.set_index("stage"))
    else:
        st.info("Nessun dato.")

with col_d2:
    st.subheader("Ultimi dataset")
    for ds in datasets[:8]:
        slug = ds.get("slug", "?")
        stage = ds.get("stage", "?")
        emoji = {"published": "✅", "incubating": "🔬", "candidate": "📥"}.get(stage, "📄")
        st.write(f"{emoji} **{slug}** · {stage}")

# -- Alert run falliti --
run_failed = [s for s in sigs if s.get("sample_run", {}).get("status") == "failed"]
if run_failed:
    st.error(f"❌ **{len(run_failed)} candidate con run CI fallito** — da rivedere")
    for s in run_failed:
        slug = s["id"].replace("-", "_")
        sr = s.get("sample_run", {}) or {}
        run_url = sr.get("run_url", "")
        label = s.get("label", slug)
        detail = s.get("detail", "")
        with st.expander(f"❌ **{label}**"):
            st.write(f"**Dettaglio:** {detail}")
            st.write(f"**Fonte:** {s.get('source_id', '?')}")
            if run_url:
                st.write(f"**Run CI:** [{run_url}]({run_url})")

# -- Pipeline errors --
if n_pipeline_err:
    st.error(f"❌ **{n_pipeline_err} pipeline in errore** — controlla Pipeline CI per dettagli")

data_freshness_note()
