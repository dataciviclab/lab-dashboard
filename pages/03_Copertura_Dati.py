"""Copertura dati — anni per dataset dal catalogo, con verifica opzionale su GCS via DuckDB."""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_catalog, data_freshness_note, verify_parquet

st.title("Copertura dati")

st.markdown(
    "Anni disponibili per ogni dataset dal catalogo. "
    "Usa la sezione **Verifica su GCS** per controllare se un parquet esiste davvero."
)

catalog = load_catalog()
datasets = catalog.get("datasets", [])

# ── Matrice dal catalogo ──────────────────────────────────────────────────────
rows = []
for ds in datasets:
    slug = ds.get("slug", "")
    period = ds.get("period", {})
    start = period.get("start")
    end = period.get("end")
    stage = ds.get("stage", "?")
    if start and end:
        for y in range(start, end + 1):
            rows.append({"dataset": slug, "stage": stage, "anno": str(y)})
    else:
        rows.append({"dataset": slug, "stage": stage, "anno": "?"})

cov_df = pd.DataFrame(rows)

if not cov_df.empty:
    pivot = cov_df.pivot_table(
        index="dataset", columns="anno", values="stage", aggfunc="first"
    ).fillna("")

    st.subheader("Matrice copertura (dal catalogo)")
    st.dataframe(pivot, use_container_width=True)

    st.subheader("Dataset per anno")
    real = cov_df[cov_df["anno"] != "?"]
    if not real.empty:
        per_year = real.groupby("anno").size().reset_index(name="dataset")
        chart = alt.Chart(per_year).mark_bar().encode(
            x=alt.X("anno:O", title="Anno"),
            y=alt.Y("dataset:Q", title="Dataset"),
            tooltip=["anno", "dataset"],
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)

        n_max = real["anno"].max()
        n_avg = real.groupby("dataset").size().mean()
        st.info(
            f"📊 **{len(datasets)}** dataset · copertura fino a **{n_max}** · "
            f"media **{n_avg:.1f}** anni/dataset"
        )

# ── Verifica su GCS via DuckDB ────────────────────────────────────────────────
st.markdown("---")
st.subheader("Verifica parquet su GCS")
st.markdown(
    "Seleziona un dataset e un anno per verificare se il parquet esiste "
    "e quanti record contiene. Usa DuckDB per leggere direttamente da GCS."
)

slug_options = [ds.get("slug", "") for ds in datasets if ds.get("period", {}).get("start")]
verify_slug = st.selectbox("Dataset", slug_options)
verify_year = st.number_input("Anno", min_value=2010, max_value=2026, value=2023, step=1)

if st.button("🔍 Verifica su GCS"):
    with st.spinner(f"Verifica {verify_slug}/{verify_year}..."):
        try:
            result = verify_parquet(verify_slug, verify_year)
            if result["records"] >= 0:
                parquet_url = (
                    f"https://storage.googleapis.com/dataciviclab-clean"
                    f"/{verify_slug}/{verify_year}"
                    f"/{verify_slug}_{verify_year}_clean.parquet"
                )
                st.success(
                    f"✅ **{verify_slug}**/{verify_year} — "
                    f"**{result['records']:,}** record"
                )
                st.markdown(
                    f"📥 **[Scarica parquet]({parquet_url})** "
                    f"— {result['records']:,} righe, formato colonnare"
                )
            else:
                st.warning("⚠️ Parquet trovato ma 0 record")
        except Exception as e:
            st.error(f"❌ Parquet non raggiungibile: {e}")

data_freshness_note()
