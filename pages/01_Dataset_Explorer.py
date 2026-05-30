"""Dataset Explorer — copertura anni e verifica parquet su GCS."""
import altair as alt
import pandas as pd
import streamlit as st
from lab_connectors.gcs.paths import https_url

from sources import data_freshness_note, load_catalog, verify_parquet

st.title("📚 Esplora dataset")

st.markdown(
    "Copertura anni dei dataset pubblicati e verifica parquet su GCS. "
    "Per query SQL avanzate, usa la pagina **Query SQL**."
)

catalog = load_catalog()
datasets = catalog.get("datasets", [])

# ── Copertura anni (ex Copertura Dati) ────────────────────────────────────
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
    col_mat, col_chart = st.columns([1.5, 1])

    with col_mat:
        pivot = cov_df.pivot_table(
            index="dataset", columns="anno", values="stage", aggfunc="first"
        ).fillna("")
        # Anni in ordine decrescente (più recente primo)
        pivot = pivot[sorted(pivot.columns, reverse=True)]
        st.subheader("Copertura anni")
        st.dataframe(pivot, use_container_width=True, height=320)

    with col_chart:
        real = cov_df[cov_df["anno"] != "?"]
        if not real.empty:
            per_year = real.groupby("anno").size().reset_index(name="dataset")
            chart = alt.Chart(per_year).mark_bar(color="#3b82f6").encode(
                x=alt.X("anno:O", title=None),
                y=alt.Y("dataset:Q", title="Dataset"),
                tooltip=["anno", "dataset"],
            ).properties(height=280)
            st.altair_chart(chart, use_container_width=True)

            n_max = real["anno"].max()
            n_avg = real.groupby("dataset").size().mean()
            st.info(
                f"📊 **{len(datasets)}** dataset · copertura fino a **{n_max}** · "
                f"media **{n_avg:.1f}** anni/dataset"
            )

st.markdown("---")

# ── Verifica parquet su GCS ────────────────────────────────────────────────
st.subheader("Verifica e scarica parquet da GCS")
st.markdown(
    "Seleziona un dataset e un anno per controllare se il parquet esiste "
    "sul bucket e quanti record contiene."
)

slug_options = [ds.get("slug", "") for ds in datasets if ds.get("period", {}).get("start")]
col_vs, col_vy, _ = st.columns([2, 1, 4])
with col_vs:
    verify_slug = st.selectbox("Dataset", slug_options)
with col_vy:
    verify_year = st.number_input(
        "Anno", min_value=2010, max_value=2026, value=2023, step=1
    )

if st.button("🔍 Verifica su GCS"):
    with st.spinner(f"Verifica {verify_slug}/{verify_year}..."):
        try:
            result = verify_parquet(verify_slug, verify_year)
            if result["records"] >= 0:
                parquet_url = https_url(
                    "clean", "clean_parquet", slug=verify_slug, year=verify_year
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

st.markdown("---")
st.caption(
    "La verifica usa DuckDB per leggere direttamente il parquet da GCS. "
    "Per query SQL avanzate, usa la pagina **Query SQL**."
)

data_freshness_note()
