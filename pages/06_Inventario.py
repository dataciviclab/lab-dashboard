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
    load_inventory_report,
    load_radar,
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
inventory_report = load_inventory_report()
inventory_sources = inventory_report.get("sources", {})

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

# ── Dettaglio fonti (unificato: radar + inventario + coverage + segnali) ──
st.subheader("Dettaglio fonti")

radar = load_radar()
registry = load_sources_registry()
catalog_signals = load_catalog_signals()

sources = radar.get("sources", [])
signals_list = catalog_signals.get("signals", [])

radar_map = {s["id"]: s for s in sources}
signals_map = {sig.get("source", ""): sig for sig in signals_list}

# Coverage map
coverage_map = {}
if not coverage_df.empty:
    for _, r in coverage_df.iterrows():
        coverage_map[r["source_id"]] = {
            "chk_items": int(r["chk_items"]),
            "inv_items": int(r["inv_items"]),
            "coverage_pct": round(r["chk_items"] / r["inv_items"] * 100, 1)
            if r["inv_items"]
            else 0,
        }

table_rows = []
for src_id, src_data in registry.items():
    radar_s = radar_map.get(src_id, {})
    inv = inventory_sources.get(src_id, {})
    sig = signals_map.get(src_id, {})

    # Badge radar
    radar_status = radar_s.get("status", "?")
    radar_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(radar_status, "⚪")

    # Badge inventario
    inv_status = inv.get("status", "")
    inv_badge = "✅" if inv_status == "ok" else ("❌" if inv_status == "error" else "—")

    # Segnale
    sig_action = sig.get("suggested_action", "")
    sig_badge = {"catalog-watch-ready": "📡", "low signal": "🔉", "nessuna": ""}.get(
        sig_action, "?"
    )

    # Coverage
    cov = coverage_map.get(src_id, {})
    chk_items = cov.get("chk_items", 0)
    cov_pct = cov.get("coverage_pct", 0)

    table_rows.append(
        {
            "id": src_id,
            "protocollo": src_data.get("protocol", "?"),
            "radar": f"{radar_emoji} {radar_status}",
            "inventario": inv_badge,
            "item_count": inv.get("rows", ""),
            "checked": chk_items if chk_items else "",
            "coverage": f"{cov_pct}%" if cov_pct else "",
            "segnale": sig_badge,
            "azione": sig_action,
            "verdict": src_data.get("verdict", "?"),
            "modalità": src_data.get("observation_mode", "?"),
        }
    )

df_table = pd.DataFrame(table_rows)

# Filtri
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    rf = st.selectbox("Filtra radar", ["Tutti", "GREEN", "YELLOW", "RED"], key="inv_filtro_radar")
with col_f2:
    vf = st.selectbox("Filtra verdict", ["Tutti", "go", "hold"], key="inv_filtro_verdict")
with col_f3:
    af = st.selectbox(
        "Filtra azione segnale",
        ["Tutti", "catalog-watch-ready", "low signal", "nessuna"],
        key="inv_filtro_segnale",
    )

filtered = df_table
if rf != "Tutti":
    filtered = filtered[filtered["radar"].str.contains(rf)]
if vf != "Tutti":
    filtered = filtered[filtered["verdict"] == vf]
if af != "Tutti":
    filtered = filtered[filtered["azione"] == af]

st.dataframe(
    filtered.drop(columns=["azione"]),
    column_config={
        "id": "Fonte",
        "protocollo": "Protocollo",
        "radar": "Radar",
        "inventario": "Inv.",
        "item_count": st.column_config.NumberColumn("Item", format="%d"),
        "checked": st.column_config.NumberColumn("Checked", format="%d"),
        "coverage": "Coverage",
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
        radar_s = radar_map.get(src_id, {})
        src_data = registry.get(src_id, {})
        inv = inventory_sources.get(src_id, {})
        sig = signals_map.get(src_id, {})

        http_code = radar_s.get("http_code", "")
        note = radar_s.get("note", "") or ""
        streak = radar_s.get("red_streak") or 0
        inv_rows = inv.get("rows", "")
        inv_method = inv.get("method", "")
        sig_topics = sig.get("topics", {})
        topics_str = ", ".join(f"{k}={v}" for k, v in sig_topics.items())
        sig_yr = sig.get("years_range", [])

        st.markdown(f"**{src_id}** — {row['radar']} · inv {row['inventario']}")
        cols = st.columns(3)
        with cols[0]:
            st.write(f"Protocollo: {src_data.get('protocol', '?')}")
            st.write(f"Modalità: {src_data.get('observation_mode', '?')}")
            st.write(f"Verdetto: {src_data.get('verdict', '?')}")
        with cols[1]:
            st.write(f"HTTP: {http_code}" if http_code else "")
            if note:
                st.write(f"Nota: {note}")
            if streak:
                st.write(f"Streak RED: {streak}g")
        with cols[2]:
            if inv_rows:
                st.write(f"Inventario: {inv_rows} righe{' · ' + inv_method if inv_method else ''}")
            if sig:
                st.write(f"Segnale: {row['segnale']} {row['azione']}")
            if topics_str:
                st.write(f"Topic: {topics_str}")
            if sig_yr:
                st.write(f"Anni: {sig_yr[0]}–{sig_yr[1]}")
        st.markdown("---")

st.caption(
    "Fonti: source-observatory (sources_registry.yaml, radar_summary.json, "
    "catalog_signals.json) · catalog_inventory_report.json (GCS) · "
    "source_check_results.parquet (GCS)"
)

data_freshness_note()
