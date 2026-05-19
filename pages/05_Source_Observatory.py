"""
Source Observatory — stato e KPI del monitoraggio fonti.
Unifica radar, inventario, segnali e funnel SO in un'unica pagina.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import (
    load_radar, load_radar_history, load_sources_registry,
    load_catalog_signals, load_inventory_report, load_signals,
    load_check_coverage,
    data_freshness_note,
)
st.title("Source Observatory")

st.markdown(
    "Stato del monitoraggio fonti: dal censimento all'intake. "
    "Il funnel mostra quante fonti arrivano a ogni stadio; "
    "la tabella sotto riassume tutti gli indicatori per fonte."
)

# ── Carica dati ───────────────────────────────────────────────────
radar = load_radar()
radar_history_data = load_radar_history()
registry = load_sources_registry()
catalog_signals = load_catalog_signals()
inventory_report = load_inventory_report()
pipeline_signals = load_signals()
coverage_df = load_check_coverage()

sources = radar.get("sources", [])
status_counts = radar.get("status_counts", {})
generated_at = radar.get("generated_at", "")
inventory_sources = inventory_report.get("sources", {})
signals_list = catalog_signals.get("signals", [])
sigs = pipeline_signals.get("signals", [])

# Build maps
radar_map = {s["id"]: s for s in sources}
signals_map = {sig.get("source", ""): sig for sig in signals_list}
coverage_map = {}
if not coverage_df.empty:
    for _, r in coverage_df.iterrows():
        coverage_map[r["source_id"]] = {
            "chk_items": int(r["chk_items"]),
            "inv_items": int(r["inv_items"]),
            "coverage_pct": round(r["chk_items"] / r["inv_items"] * 100, 1)
            if r["inv_items"] else 0,
        }
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
    col_c3.metric("✅ Raggiungibili", f"{tot_reachable:,}",
                  f"{round(tot_reachable/tot_chk*100,1) if tot_chk else 0}%")
    col_c4.metric("🎯 Intake candidate", f"{tot_candidates:,}",
                  f"{round(tot_candidates/tot_chk*100,1) if tot_chk else 0}%")

    # Bar chart orizzontale: inventario vs checked per fonte (top 10 per inv_items)
    plot_df = coverage_df[coverage_df["inv_items"] > 0].copy()
    plot_df["coverage_pct"] = (
        (plot_df["chk_items"] / plot_df["inv_items"] * 100).round(1)
    )
    plot_df = plot_df.sort_values("inv_items", ascending=True).tail(15)

    # Melt per barre affiancate
    melt_df = plot_df.melt(
        id_vars=["source_id", "coverage_pct"],
        value_vars=["inv_items", "chk_items"],
        var_name="tipo", value_name="items",
    )
    melt_df["tipo"] = melt_df["tipo"].map({
        "inv_items": "Inventario", "chk_items": "Checked",
    })

    bars = alt.Chart(melt_df).mark_bar().encode(
        x=alt.X("items:Q", title="Items"),
        y=alt.Y("source_id:N", title=None, sort=plot_df["source_id"].tolist()),
        color=alt.Color(
            "tipo:N",
            scale={"domain": ["Inventario", "Checked"],
                   "range": ["#94a3b8", "#3b82f6"]},
            title=None,
        ),
        tooltip=[
            alt.Tooltip("source_id:N", title="Fonte"),
            alt.Tooltip("tipo:N", title="Tipo"),
            alt.Tooltip("items:Q", title="Items", format=","),
            alt.Tooltip("coverage_pct:Q", title="Coverage %", format=".1f"),
        ],
    ).properties(height=320)

    st.altair_chart(bars, use_container_width=True)

    # Tabella compatta coverage
    cov_table = coverage_df[coverage_df["inv_items"] > 0].copy()
    cov_table["coverage_pct"] = (
        (cov_table["chk_items"] / cov_table["inv_items"] * 100).round(1)
    )
    cov_table = cov_table.sort_values("inv_items", ascending=False).reset_index(drop=True)

    st.dataframe(
        cov_table,
        column_config={
            "source_id": "Fonte",
            "inv_items": st.column_config.NumberColumn("Inventario", format="%d"),
            "chk_items": st.column_config.NumberColumn("Checked", format="%d"),
            "reachable": st.column_config.NumberColumn("Raggiungibili", format="%d"),
            "candidates": st.column_config.NumberColumn("Candidate", format="%d"),
            "coverage_pct": st.column_config.NumberColumn("Coverage %", format="%.1f"),
        },
        hide_index=True,
        use_container_width=True,
        height=min(40 * len(cov_table) + 35, 480),
    )
else:
    st.info("Dati copertura non disponibili.")

st.caption(
    "Fonte: catalog_inventory_latest.parquet × source_check_results.parquet su GCS. "
    "Il coverage indica quanti items del catalogo sono stati effettivamente "
    "scaricati e profilati da source-check."
)
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
            x=alt.X("data:T", title="Data"),
            y=alt.Y("fonte:N", title="Fonte", sort=fonte_order),
            color=alt.Color(
                "stato:N",
                scale={"domain": ["GREEN", "YELLOW", "RED", "?"],
                       "range": ["#16a34a", "#fbbf24", "#dc2626", "#94a3b8"]},
                title="Stato",
            ),
            tooltip=["data:T", "fonte:N", "stato:N"],
        ).properties(height=320)
        st.altair_chart(heat, use_container_width=True)
    else:
        st.info("Nessun dato storico disponibile.")
else:
    st.info("Storico probe non ancora disponibile.")

st.markdown("---")

# ── Tabella fonti unificata ───────────────────────────────────────
st.subheader("Dettaglio fonti")

# Costruisci dataframe riepilogativo
table_rows = []
for src_id, src_data in registry.items():
    radar_s = radar_map.get(src_id, {})
    inv = inventory_sources.get(src_id, {})
    sig = signals_map.get(src_id, {})

    # Badge radar
    radar_status = radar_s.get("status", "?")
    radar_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(
        radar_status, "⚪")

    # Badge inventario
    inv_status = inv.get("status", "")
    inv_badge = ("✅" if inv_status == "ok"
                 else ("❌" if inv_status == "error" else "—"))

    # Segnale
    sig_action = sig.get("suggested_action", "")
    sig_badge = {"catalog-watch-ready": "📡",
                 "low signal": "🔉", "nessuna": ""}.get(sig_action, "?")

    # Coverage (da source_check_results)
    cov = coverage_map.get(src_id, {})
    chk_items = cov.get("chk_items", 0)
    cov_pct = cov.get("coverage_pct", 0)

    table_rows.append({
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
    })

df_table = pd.DataFrame(table_rows)

# Filtri
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    rf = st.selectbox("Filtra radar", ["Tutti", "GREEN", "YELLOW", "RED"])
with col_f2:
    vf = st.selectbox("Filtra verdict", ["Tutti", "go", "hold"])
with col_f3:
    af = st.selectbox("Filtra azione segnale",
                      ["Tutti", "catalog-watch-ready", "low signal", "nessuna"])

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

# ── Expander dettaglio per fonte ──────────────────────────────────
with st.expander("🔍 Vedi dettaglio completo per fonte"):
    for _, row in filtered.iterrows():
        src_id = row["id"]
        radar_s = radar_map.get(src_id, {})
        src_data = registry.get(src_id, {})
        inv = inventory_sources.get(src_id, {})
        sig = signals_map.get(src_id, {})

        http_code = radar_s.get("http_code", "")
        note = radar_s.get("note", "") or ""
        streak = (radar_s.get("red_streak") or 0)
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
                st.write(f"Inventario: {inv_rows} righe"
                         f"{' · ' + inv_method if inv_method else ''}")
            if sig:
                st.write(f"Segnale: {row['segnale']} {row['azione']}")
            if topics_str:
                st.write(f"Topic: {topics_str}")
            if sig_yr:
                st.write(f"Anni: {sig_yr[0]}–{sig_yr[1]}")
        st.markdown("---")

st.markdown("---")
data_freshness_note()

st.caption(
    "Fonti: source-observatory (sources_registry.yaml, radar_summary.json, "
    "radar_history.json, catalog_signals.json) · "
    "catalog_inventory_report.json (GCS) · pipeline_signals.json (DI)"
)
