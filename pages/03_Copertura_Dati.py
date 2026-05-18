"""Copertura dati — anni disponibili per dataset, letti dal catalogo."""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_catalog, render_sidebar_common, data_freshness_note

render_sidebar_common()

st.title("Copertura dati")

st.markdown(
    "Anni disponibili per ogni dataset, letti dal catalogo. "
    "I periodi sono estratti da `clean_catalog.json`."
)

catalog = load_catalog()
datasets = catalog.get("datasets", [])

# Costruisci matrice copertura dal catalogo
rows = []
for ds in datasets:
    slug = ds.get("slug", "")
    period = ds.get("period", {})
    start = period.get("start")
    end = period.get("end")
    stage = ds.get("stage", "?")
    if start and end:
        for y in range(start, end + 1):
            rows.append({"dataset": slug, "stage": stage, "anno": y})
    else:
        rows.append({"dataset": slug, "stage": stage, "anno": "?"})

cov_df = pd.DataFrame(rows)

if not cov_df.empty:
    # Pivot: dataset × anno
    pivot = cov_df.pivot_table(
        index="dataset", columns="anno", values="stage", aggfunc="first"
    ).fillna("")

    st.subheader("Matrice copertura (dal catalogo)")
    st.dataframe(pivot, use_container_width=True)

    # Conteggio dataset per anno
    st.subheader("Dataset per anno")
    per_year = cov_df[cov_df["anno"] != "?"].groupby("anno").size().reset_index(name="dataset")
    chart = alt.Chart(per_year).mark_bar().encode(
        x=alt.X("anno:O", title="Anno"),
        y=alt.Y("dataset:Q", title="Dataset"),
        tooltip=["anno", "dataset"],
    ).properties(height=350)
    st.altair_chart(chart, use_container_width=True)

    # Stat
    max_year = cov_df[cov_df["anno"] != "?"]["anno"].max()
    st.info(
        f"📊 **{len(datasets)}** dataset · copertura **{max_year}** anni · "
        f"media **{cov_df[cov_df['anno'] != '?'].groupby('dataset').size().mean():.1f}** anni/dataset"
    )
else:
    st.warning("Nessun dato di copertura disponibile dal catalogo.")

data_freshness_note()
