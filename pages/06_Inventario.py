"""
Inventario — items nei cataloghi, source check e dettaglio fonti.
"""

import pandas as pd
import streamlit as st

from sources import (
    data_freshness_note,
    load_catalog_signals,
    load_radar,
    load_sources_dashboard,
    load_sources_registry,
)

st.title("📦 Inventario")

st.markdown(
    "Items censiti nei cataloghi delle fonti monitorate, quanti sono stati "
    "scored/reachable dal source-check, e dettaglio per fonte."
)

# ── Carica dati (report v2 SO, unica fonte) ────────────────────────
dashboard = load_sources_dashboard()
radar = load_radar()
registry = load_sources_registry()
catalog_signals = load_catalog_signals()

sources = radar.get("sources", [])
dash_list = dashboard.get("sources", [])
signals_list = catalog_signals.get("signals", [])

radar_map = {s["id"]: s for s in sources}
dash_map = {d["source_id"]: d for d in dash_list}
signals_map = {sig.get("source_id", ""): sig for sig in signals_list}

# ── KPI aggregati (dal report v2) ─────────────────────────────────
summary = dashboard.get("summary", {})
tot_inv = summary.get("tot_inventory_items", 0)
tot_scored = summary.get("tot_scored_items", 0)
tot_reachable = summary.get("tot_reachable", 0)
tot_in_use = summary.get("tot_datasets_in_use", 0)
coverage_pct = round(tot_scored / tot_inv * 100, 1) if tot_inv else 0

col_c1, col_c2, col_c3, col_c4 = st.columns(4)
col_c1.metric("📦 Items inventario", f"{tot_inv:,}")
col_c2.metric("🔍 Items scored", f"{tot_scored:,}", f"{coverage_pct}% coverage")
col_c3.metric(
    "✅ Raggiungibili",
    f"{tot_reachable:,}",
    f"{round(tot_reachable / tot_scored * 100, 1) if tot_scored else 0}%",
)
col_c4.metric("🧩 Dataset in uso", f"{tot_in_use:,}")

st.markdown("---")

# ── Dettaglio fonti (unificato: dashboard SO v2 + radar + registry + segnali) ──
st.subheader("Dettaglio fonti")

st.caption(
    "Per il deep-dive su una singola fonte usa **🔍 Scheda fonte** (menu Source Observatory)."
)

# Verdict report v2 → etichetta leggibile
_VERDICT_LABEL = {
    "STABLE": "stabile",
    "INVENTORY_CHANGED": "inventario cambiato",
    "PARTIALLY_SCOPED": "scoping parziale",
}


def _verdict_label(v: str) -> str:
    return _VERDICT_LABEL.get(v, v or "?")


def _readiness_badge(score) -> str:
    """Readiness 0-10 → emoji + numero."""
    if score is None:
        return "—"
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "—"
    if score >= 8:
        return f"🟢 {score:g}"
    if score >= 4:
        return f"🟡 {score:g}"
    return f"🔴 {score:g}"


table_rows = []
for src_id, src_data in registry.items():
    dash = dash_map.get(src_id, {})
    radar_s = radar_map.get(src_id, {})
    sig = signals_map.get(src_id, {})

    # Badge radar
    radar_status = radar_s.get("status", dash.get("radar", "?"))
    radar_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(radar_status, "⚪")

    # Segnale (schema v2: result + metric_value)
    sig_result = sig.get("result", "")
    sig_value = sig.get("metric_value")
    if sig_result and sig_value is not None:
        segnale = f"{sig_result} · {sig_value}"
    elif sig_result:
        segnale = sig_result
    else:
        segnale = "—"

    verdict = dash.get("verdict", src_data.get("verdict", "?"))
    n_use = dash.get("datasets_in_use")
    readiness = dash.get("avg_readiness")

    table_rows.append(
        {
            "id": src_id,
            "protocollo": dash.get("protocol", src_data.get("protocol", "?")),
            "radar": f"{radar_emoji} {radar_status}",
            "item_count": dash.get("inventory_items", ""),
            "scored": dash.get("scored_items", ""),
            "reachable": dash.get("reachable", ""),
            "readiness_num": readiness if readiness is not None else "",
            "readiness": _readiness_badge(readiness),
            "in_uso": n_use if n_use is not None else "",
            "segnale": segnale,
            "verdict": _verdict_label(verdict),
            "modalità": src_data.get("observation_mode", "?"),
        }
    )

df_table = pd.DataFrame(table_rows)

# Filtri
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    rf = st.selectbox("Filtra radar", ["Tutti", "GREEN", "YELLOW", "RED"], key="inv_filtro_radar")
with col_f2:
    vf = st.selectbox(
        "Filtra verdict",
        ["Tutti", "stabile", "inventario cambiato", "scoping parziale"],
        key="inv_filtro_verdict",
    )
with col_f3:
    read_f = st.selectbox(
        "Filtra readiness",
        ["Tutti", "🟢 alta (≥8)", "🟡 media (4–7.9)", "🔴 bassa (<4)"],
        key="inv_filtro_readiness",
    )

filtered = df_table
if rf != "Tutti":
    filtered = filtered[filtered["radar"].str.contains(rf)]
if vf != "Tutti":
    filtered = filtered[filtered["verdict"] == vf]
if read_f != "Tutti":
    rn = pd.to_numeric(filtered["readiness_num"], errors="coerce")
    if read_f.startswith("🟢"):
        filtered = filtered[rn >= 8]
    elif read_f.startswith("🟡"):
        filtered = filtered[(rn >= 4) & (rn < 8)]
    elif read_f.startswith("🔴"):
        filtered = filtered[(rn < 4) & rn.notna()]

st.dataframe(
    filtered.drop(columns=["readiness_num"]),
    column_config={
        "id": "Fonte",
        "protocollo": "Protocollo",
        "radar": "Radar",
        "item_count": st.column_config.NumberColumn("Item", format="%d"),
        "scored": st.column_config.NumberColumn("Scored", format="%d"),
        "reachable": st.column_config.NumberColumn("Raggiung.", format="%d"),
        "readiness": "Readiness",
        "in_uso": st.column_config.NumberColumn("In uso", format="%d"),
        "segnale": "Segnale",
        "verdict": "Verdetto",
        "modalità": "Modalità",
    },
    hide_index=True,
    width="stretch",
    height=min(45 * len(filtered) + 35, 600),
)

st.caption(
    "Fonti: source-observatory (sources_dashboard.json · radar_summary.json · "
    "sources_registry.yaml · catalog_signals.json)"
)

data_freshness_note()
