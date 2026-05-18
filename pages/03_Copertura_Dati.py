"""Copertura dati — matrice anni×dataset da parquet GCS."""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_catalog, duckdb_query

st.title("Copertura dati")

catalog = load_catalog()
datasets = catalog.get("datasets", [])

st.markdown("Record per dataset/anno letti live dai parquet su GCS via DuckDB.")

YEARS = list(range(2019, 2026))

if st.button("Carica copertura live da GCS"):
    with st.spinner("Caricamento dati da GCS..."):
        rows = []
        for ds in datasets[:15]:
            slug = ds.get("slug", "")
            for y in YEARS:
                path = (
                    f"https://storage.googleapis.com/dataciviclab-clean/"
                    f"{slug}/{y}/{slug}_{y}_clean.parquet"
                )
                try:
                    df = duckdb_query(
                        f"SELECT '{slug}' AS dataset, {y} AS anno, "
                        f"COUNT(*) AS records FROM read_parquet('{path}')"
                    )
                    rows.append(df)
                except Exception:
                    pass

        if rows:
            cov_df = pd.concat(rows, ignore_index=True)
            cov_pivot = cov_df.pivot_table(
                index="dataset", columns="anno", values="records", aggfunc="sum"
            ).fillna(0).astype(int)
            cov_pivot = cov_pivot.replace(0, pd.NA)

            st.subheader("Matrice copertura")
            st.dataframe(cov_pivot, use_container_width=True)

            st.subheader("Record totali per dataset")
            totals = cov_df.groupby("dataset")["records"].sum().reset_index()
            chart = alt.Chart(totals).mark_bar().encode(
                x=alt.X("dataset:N", title="Dataset", sort="-y"),
                y=alt.Y("records:Q", title="Record totali"),
                color=alt.Color("dataset:N", legend=None),
                tooltip=["dataset", "records"],
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)

            st.caption(f"Totale record: {cov_df['records'].sum():,}")
        else:
            st.info("Nessun dato caricato. Possibili errori di connessione a GCS.")
else:
    st.info(
        "Premi 'Carica copertura live da GCS' per leggere i parquet "
        "con DuckDB. Richiede ~10-20 secondi per 15 dataset."
    )
