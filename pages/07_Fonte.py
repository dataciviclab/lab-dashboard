"""
Scheda fonte — deep-dive per singola fonte del Source Observatory.
Consuma source_reports/{source_id}.json (report v1):
health, inventory (con drift vs baseline), source_check, datasets_in_use,
signals, operational_verdict.
"""

import pandas as pd
import streamlit as st

from sources import (
    data_freshness_note,
    load_explorer_datasets,
    load_source_report,
    load_sources_dashboard,
    load_sources_registry,
)

st.title("🔍 Scheda fonte")

# ── Selezione fonte ────────────────────────────────────────────────
registry = load_sources_registry()
dashboard = load_sources_dashboard()
dash_map = {d["source_id"]: d for d in dashboard.get("sources", [])}

source_ids = sorted(registry.keys())
if not source_ids:
    st.error("Registro fonti non disponibile.")
    st.stop()

selected = st.selectbox("Fonte", source_ids, key="fonte_scheda_id")

report = load_source_report(selected)
if not report:
    st.warning(f"Nessun report disponibile per **{selected}**.")
    st.stop()

# ── Identity ───────────────────────────────────────────────────────
identity = report.get("identity", {})
dash = dash_map.get(selected, {})

st.subheader(selected)
st.caption(identity.get("base_url", ""))

if identity.get("note"):
    st.markdown(f"*{identity['note']}*")

# ── Verdict operativo ──────────────────────────────────────────────
ov = report.get("operational_verdict", {})
ov_label = ov.get("label", "?")
ov_icon = {"STABLE": "✅", "INVENTORY_CHANGED": "🔄", "PARTIALLY_SCOPED": "🟡"}.get(ov_label, "⚪")
next_action = ov.get("next_action")
col_ov1, col_ov2 = st.columns(2)
with col_ov1:
    st.metric("Verdict operativo", f"{ov_icon} {ov_label}")
with col_ov2:
    st.metric("Azioni", next_action or "—")

# ── KPI: health + inventory + source_check ─────────────────────────
health = report.get("health", {})
inventory = report.get("inventory", {})
sc = report.get("source_check", {})

radar_status = health.get("radar_status", dash.get("radar", "?"))
n_items = inventory.get("total_items", dash.get("inventory_items"))
n_scored = sc.get("total_scored", dash.get("scored_items"))
n_reachable = sc.get("reachable", dash.get("reachable"))
avg_read = sc.get("avg_readiness", dash.get("avg_readiness"))
n_use = dash.get("datasets_in_use")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Radar", radar_status)
col2.metric("Items inventario", f"{n_items:,}" if n_items else "—")
col3.metric("Scored", f"{n_scored:,}" if n_scored else "—")
col4.metric("Raggiungibili", f"{n_reachable:,}" if n_reachable else "—")
col5.metric("Readiness", f"{avg_read:g}" if avg_read is not None else "—")

# ── Inventory + drift vs baseline ──────────────────────────────────
st.subheader("Inventario")

inv_delta = inventory.get("delta")
inv_delta_pct = inventory.get("delta_pct")
base_value = inventory.get("baseline_value")
base_date = inventory.get("baseline_date")
captured_at = inventory.get("captured_at", "")

if inv_delta is not None:
    drift = "🔴 +" if inv_delta > 0 else ("🟢 " if inv_delta < 0 else "⚪ ")
    drift_txt = (
        f"{drift}{inv_delta:,} ({inv_delta_pct:+.1f}%)"
        if inv_delta_pct is not None
        else f"{drift}{inv_delta:,}"
    )
    st.metric(
        "Drift vs baseline",
        drift_txt,
        f"baseline {base_value:,} ({base_date})" if base_value else "",
    )
else:
    st.metric("Items inventario", f"{n_items:,}" if n_items else "—")

st.caption(f"Ultimo inventory: {captured_at}" if captured_at else "")

formats = inventory.get("formats", {})
if formats:
    fmt_df = pd.DataFrame(
        [{"formato": k, "items": v} for k, v in sorted(formats.items(), key=lambda x: -x[1])]
    )
    st.dataframe(fmt_df, hide_index=True, width="stretch")

# ── Source check ───────────────────────────────────────────────────
st.subheader("Source check")

coverage_pct = sc.get("coverage_pct")
st.metric("Coverage scored", f"{coverage_pct}%" if coverage_pct is not None else "—")

top = sc.get("top_items", [])
if top:
    st.markdown("**Top items**")
    top_df = pd.DataFrame(top)[["name", "score", "format", "reachable"]]
    st.dataframe(
        top_df,
        hide_index=True,
        width="stretch",
        column_config={
            "name": "Item",
            "score": st.column_config.NumberColumn("Score", format="%d"),
            "format": "Formato",
            "reachable": "Raggiungibile",
        },
    )

formato_aperto = sc.get("formato_aperto", {})
if formato_aperto:
    st.caption(
        f"Formato aperto: score {formato_aperto.get('score')} · "
        f"{formato_aperto.get('perc_aperto')}% aperti · "
        f"{formato_aperto.get('perc_reachable')}% raggiungibili"
    )

# ── Dataset in uso (bridge fonte → catalogo) ───────────────────────
st.subheader("Dataset in uso")

datasets_use = report.get("datasets_in_use", [])
if datasets_use:
    explorer_slugs = load_explorer_datasets()
    de_map = {
        "aifa_spesa_consumo": "spesa-farmaceutica",
        "ispra_ru_base": "rifiuti-urbani",
        "civile_flussi": "flussi-giustizia-civile",
        "terna_capacita_rinnovabile": "capacita-rinnovabile",
        "terna_electricity_by_source": "produzione-elettrica-fonti",
        "bdap_entrate_stato": "entrate-stato",
        "inps_pensioni_trimestrale": "pensioni-inps",
    }

    def _de_slug(slug: str) -> str:
        return de_map.get(slug, slug.replace("_", "-"))

    for ds in datasets_use:
        slug = ds.get("slug", "?")
        status = ds.get("status", "?")
        badge = "✅ published" if status == "published" else f"⚪ {status}"
        de = _de_slug(slug)
        if de in explorer_slugs:
            st.markdown(
                f"**{slug}** · {badge} · "
                f"[Explorer](https://dataciviclab.github.io/data-explorer/dataset/{de})"
            )
        else:
            st.markdown(f"**{slug}** · {badge} · (non su Explorer)")
else:
    st.info("Nessun dataset derivato censito per questa fonte.")

# ── Signals ────────────────────────────────────────────────────────
signals = report.get("signals", [])
if signals:
    st.subheader("Segnali")
    for s in signals:
        st.write(f"- **{s.get('result', '?')}** — {s.get('detail', '')}")

st.markdown("---")
st.caption(f"Report: source-observatory/data/reports/source_reports/{selected}.json")
data_freshness_note()
