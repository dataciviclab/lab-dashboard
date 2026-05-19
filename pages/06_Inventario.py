"""
Inventario — items nei cataloghi e copertura source check.
Quanto abbiamo censito e quanto abbiamo effettivamente controllato.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import (
    load_check_coverage, load_inventory_report,
    data_freshness_note,
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
    col_c3.metric("✅ Raggiungibili", f"{tot_reachable:,}",
                  f"{round(tot_reachable/tot_chk*100,1) if tot_chk else 0}%")
    col_c4.metric("🎯 Intake candidate", f"{tot_candidates:,}",
                  f"{round(tot_candidates/tot_chk*100,1) if tot_chk else 0}%")

    # Bar chart orizzontale: inventario vs checked per fonte
    plot_df = coverage_df[coverage_df["inv_items"] > 0].copy()
    plot_df["coverage_pct"] = (
        (plot_df["chk_items"] / plot_df["inv_items"] * 100).round(1)
    )
    plot_df = plot_df.sort_values("inv_items", ascending=True).tail(15)

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

# ── Report inventario per fonte ───────────────────────────────────
st.subheader("Stato inventario per fonte")

inv_rows = []
for src_id, src_data in inventory_sources.items():
    badge = "✅" if src_data.get("status") == "ok" else "❌"
    inv_rows.append({
        "fonte": src_id,
        "stato": badge,
        "items": src_data.get("rows", ""),
        "metodo": src_data.get("method", "") or "",
    })

if inv_rows:
    inv_df = pd.DataFrame(inv_rows)
    st.dataframe(
        inv_df,
        column_config={
            "fonte": "Fonte",
            "stato": "Stato",
            "items": st.column_config.NumberColumn("Items", format="%d"),
            "metodo": "Metodo",
        },
        hide_index=True,
        use_container_width=True,
        height=min(45 * len(inv_df) + 35, 500),
    )
else:
    st.info("Dati inventario non disponibili.")

data_freshness_note()
