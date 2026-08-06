"""
Inventario — items nei cataloghi e copertura source check.
Quanto abbiamo censito e quanto abbiamo effettivamente controllato.
"""

import altair as alt
import pandas as pd
import streamlit as st

from sources import (
    data_freshness_note,
    load_catalog_signals,
    load_check_coverage,
    load_radar,
    load_sources_dashboard,
    load_sources_registry,
)

st.title("📦 Inventario")

st.markdown(
    "Items censiti nei cataloghi delle fonti monitorate, "
    "e quanti sono stati effettivamente scaricati e profilati "
    "dal source-check."
)

# ── Carica dati ───────────────────────────────────────────────────
coverage_df = load_check_coverage()

# ── Copertura source check ────────────────────────────────────────
st.subheader("Copertura source check")

if not coverage_df.empty:
    tot_inv = int(coverage_df["inv_items"].sum())
    tot_chk = int(coverage_df["chk_items"].sum())
    tot_reachable = int(coverage_df["reachable"].sum())
    tot_candidates = int(coverage_df["candidates"].sum())
    coverage_pct = round(tot_chk / tot_inv * 100, 1) if tot_inv else 0

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("📦 Items inventario", f"{tot_inv:,}")
    col_c2.metric("🔍 Items checked", f"{tot_chk:,}", f"{coverage_pct}% coverage")
    col_c3.metric(
        "✅ Raggiungibili",
        f"{tot_reachable:,}",
        f"{round(tot_reachable / tot_chk * 100, 1) if tot_chk else 0}%",
    )
    col_c4.metric(
        "🎯 Intake candidate",
        f"{tot_candidates:,}",
        f"{round(tot_candidates / tot_chk * 100, 1) if tot_chk else 0}%",
    )

    # Bar chart orizzontale: inventario (grigio) con checked (blu) dentro
    plot_df = coverage_df[coverage_df["inv_items"] > 0].copy()
    plot_df["coverage_pct"] = (plot_df["chk_items"] / plot_df["inv_items"] * 100).round(1)
    plot_df = plot_df.sort_values("inv_items", ascending=True).tail(15)

    inv_bars = (
        alt.Chart(plot_df)
        .mark_bar(color="#94a3b8")
        .encode(
            x=alt.X("inv_items:Q", title="Items"),
            y=alt.Y("source_id:N", title=None, sort=plot_df["source_id"].tolist()),
            tooltip=[
                alt.Tooltip("source_id:N", title="Fonte"),
                alt.Tooltip("inv_items:Q", title="Inventario", format=","),
                alt.Tooltip("chk_items:Q", title="Checked", format=","),
                alt.Tooltip("coverage_pct:Q", title="Coverage %", format=".1f"),
            ],
        )
    )

    chk_bars = (
        alt.Chart(plot_df)
        .mark_bar(color="#3b82f6")
        .encode(
            x=alt.X("chk_items:Q"),
            y=alt.Y("source_id:N", title=None, sort=plot_df["source_id"].tolist()),
        )
    )

    layered = (inv_bars + chk_bars).properties(height=320)

    st.altair_chart(layered, use_container_width=True)

else:
    st.info("Dati copertura non disponibili.")

st.markdown("---")

# ── Dettaglio fonti (unificato: dashboard SO v2 + radar + registry + segnali) ──
st.subheader("Dettaglio fonti")

st.caption(
    "Per il deep-dive su una singola fonte usa **🔍 Scheda fonte** (menu Source Observatory)."
)

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

    table_rows.append(
        {
            "id": src_id,
            "protocollo": dash.get("protocol", src_data.get("protocol", "?")),
            "radar": f"{radar_emoji} {radar_status}",
            "item_count": dash.get("inventory_items", ""),
            "scored": dash.get("scored_items", ""),
            "reachable": dash.get("reachable", ""),
            "readiness": _readiness_badge(dash.get("avg_readiness")),
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
    sf = st.selectbox("Filtra segnale", ["Tutti", "stable", "unstable"], key="inv_filtro_segnale")

filtered = df_table
if rf != "Tutti":
    filtered = filtered[filtered["radar"].str.contains(rf)]
if vf != "Tutti":
    filtered = filtered[filtered["verdict"] == vf]
if sf != "Tutti":
    filtered = filtered[filtered["segnale"].str.startswith(sf)]

st.dataframe(
    filtered,
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
    use_container_width=True,
    height=min(45 * len(filtered) + 35, 600),
)

# Expander dettaglio per fonte
with st.expander("🔍 Vedi dettaglio completo per fonte"):
    for _, row in filtered.iterrows():
        src_id = row["id"]
        dash = dash_map.get(src_id, {})
        radar_s = radar_map.get(src_id, {})
        src_data = registry.get(src_id, {})
        sig = signals_map.get(src_id, {})

        http_code = radar_s.get("http_code", "")
        note = radar_s.get("note", "") or ""
        streak = radar_s.get("red_streak") or 0
        sig_detail = sig.get("detail", "")
        last_inv = dash.get("last_inventory", "")

        st.markdown(f"**{src_id}** — {row['radar']} · verdict {row['verdict']}")
        cols = st.columns(3)
        with cols[0]:
            st.write(f"Protocollo: {row['protocollo']}")
            st.write(f"Modalità: {row['modalità']}")
            st.write(f"Readiness: {row['readiness']}")
        with cols[1]:
            st.write(f"HTTP: {http_code}" if http_code else "")
            if note:
                st.write(f"Nota: {note}")
            if streak:
                st.write(f"Streak RED: {streak}g")
            if last_inv:
                st.write(f"Ultimo inventory: {last_inv}")
        with cols[2]:
            if row["item_count"]:
                st.write(f"Inventario: {row['item_count']} items")
            if row["in_uso"]:
                st.write(f"Dataset in uso: {row['in_uso']}")
            if sig_detail:
                st.write(f"Segnale: {sig_detail}")
        st.markdown("---")

st.caption(
    "Fonti: source-observatory (sources_dashboard.json · radar_summary.json · "
    "sources_registry.yaml · catalog_signals.json) · "
    "catalog_inventory_report.json (GCS)"
)

data_freshness_note()
