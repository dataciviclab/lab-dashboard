"""Catalogo — esplora dataset con filtri, tabella e copertura anni."""

import altair as alt
import pandas as pd
import streamlit as st
from lab_connectors.gcs.paths import https_url

from sources import data_freshness_note, load_catalog, verify_parquet

st.title("📚 Catalogo")

catalog = load_catalog()
datasets = catalog.get("datasets", [])

if not datasets:
    st.error("Catalogo non disponibile.")
    st.stop()

# ── KPI ─────────────────────────────────────────────────────────
n_total = len(datasets)
n_published = sum(1 for d in datasets if d.get("stage") == "published")
n_incubating = n_total - n_published
by_source = {}
for d in datasets:
    sid = d.get("source_id") or d.get("source", "unknown")
    by_source[sid] = by_source.get(sid, 0) + 1
n_sources = len(by_source)
categories = {d.get("category", "") for d in datasets if d.get("category")}
n_categories = len(categories)

col1, col2, col3, col4 = st.columns(4)
col1.metric("📚 Dataset", n_total)
col2.metric("✅ Pubblicati", n_published)
col3.metric("🔬 Incubazione", n_incubating)
col4.metric("🏷️ Fonti", n_sources)

st.markdown("---")

# ── Filtri ───────────────────────────────────────────────────────
st.subheader("Filtri")

source_options = sorted(by_source.keys(), key=lambda s: -by_source[s])
source_counts = {s: by_source[s] for s in source_options}
stage_options = ["Tutti", "published", "incubating"]
cat_options = ["Tutti"] + sorted(categories)

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    src_filter = st.selectbox(
        "Fonte (source_id)",
        ["Tutti"] + [f"{s} ({source_counts[s]})" for s in source_options],
        key="cat_src",
    )
with col_f2:
    stage_filter = st.selectbox("Stage", stage_options, key="cat_stage")
with col_f3:
    cat_filter = st.selectbox("Categoria", cat_options, key="cat_cat")

search = st.text_input("Cerca", placeholder="slug, nome o descrizione...", key="cat_search")

# Applica filtri
filtered = datasets
if src_filter != "Tutti":
    src_id = src_filter.split(" (")[0]
    filtered = [d for d in filtered if (d.get("source_id") or d.get("source")) == src_id]
if stage_filter != "Tutti":
    filtered = [d for d in filtered if d.get("stage") == stage_filter]
if cat_filter != "Tutti":
    filtered = [d for d in filtered if d.get("category") == cat_filter]
if search:
    q = search.lower()
    filtered = [
        d
        for d in filtered
        if q in d.get("slug", "").lower()
        or q in d.get("name", "").lower()
        or q in d.get("description", "").lower()
    ]

st.write(f"**{len(filtered)} dataset** trovati")

# ── Tabella ──────────────────────────────────────────────────────
rows = []
for ds in filtered:
    period = ds.get("period", {})
    start = period.get("start", "?")
    end = period.get("end", "?")
    yrs = f"{start}–{end}" if start != "?" else "?"
    tags = ds.get("tags", [])
    n_cols = len(ds.get("columns", []))
    stage_icon = "✅" if ds.get("stage") == "published" else "🔬"
    rows.append(
        {
            "slug": ds.get("slug", ""),
            "nome": ds.get("name", "")[:50],
            "fonte": ds.get("source_id") or ds.get("source", "?"),
            "stage": f"{stage_icon} {ds.get('stage', '?')}",
            "anni": yrs,
            "tags": ", ".join(tags[:3]),
            "schema": f"{n_cols} colonne" if n_cols else "—",
        }
    )

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        column_config={
            "slug": st.column_config.TextColumn("Slug", width="medium"),
            "nome": st.column_config.TextColumn("Nome", width="medium"),
            "fonte": st.column_config.TextColumn("Fonte", width="small"),
            "stage": st.column_config.TextColumn("Stage", width="small"),
            "anni": st.column_config.TextColumn("Anni", width="small"),
            "tags": st.column_config.TextColumn("Tags", width="small"),
            "schema": st.column_config.TextColumn("Schema", width="small"),
        },
        hide_index=True,
        width="stretch",
        height=min(40 * len(rows) + 35, 500),
    )

    # Expander dettaglio per ogni dataset
    for ds in filtered:
        slug = ds.get("slug", "")
        loc = ds.get("location", {})
        cols = ds.get("columns", [])
        with st.expander(f"**{slug}** — {ds.get('name', '')}"):
            st.write(f"**Descrizione:** {ds.get('description', '—')}")
            st.write(f"**Fonte:** {ds.get('source_id') or ds.get('source', '?')}")
            period = ds.get("period", {})
            st.write(f"**Anni:** {period.get('start', '?')}–{period.get('end', '?')}")
            st.write(f"**Stage:** {ds.get('stage', '?')}")
            if loc.get("path"):
                st.write(f"**GCS:** `{loc['path']}`")
            if cols:
                st.markdown("**Schema colonne**")
                col_df = pd.DataFrame(
                    [
                        {
                            "colonna": c.get("name", "?"),
                            "tipo": c.get("type", "?"),
                            "ruolo": c.get("role", "?"),
                            "desc": c.get("description", ""),
                        }
                        for c in cols
                    ]
                )
                st.dataframe(col_df, hide_index=True, width="stretch")
else:
    st.info("Nessun dataset trovato con i filtri selezionati.")

st.markdown("---")

# ── Copertura anni ───────────────────────────────────────────────
st.subheader("Copertura anni")

year_rows = []
for ds in datasets:
    slug = ds.get("slug", "")
    period = ds.get("period", {})
    start = period.get("start")
    end = period.get("end")
    stage = ds.get("stage", "?")
    if start and end:
        for y in range(start, end + 1):
            year_rows.append({"dataset": slug, "stage": stage, "anno": str(y)})

if year_rows:
    cov_df = pd.DataFrame(year_rows)
    col_mat, col_chart = st.columns([1.5, 1])
    with col_mat:
        pivot = cov_df.pivot_table(
            index="dataset", columns="anno", values="stage", aggfunc="first"
        ).fillna("")
        pivot = pivot[sorted(pivot.columns, reverse=True)]
        st.dataframe(pivot, width="stretch", height=320)
    with col_chart:
        real = cov_df[cov_df["anno"] != "?"]
        if not real.empty:
            per_year = real.groupby("anno").size().reset_index(name="dataset")
            chart = (
                alt.Chart(per_year)
                .mark_bar(color="#3b82f6")
                .encode(
                    x=alt.X("anno:O", title=None),
                    y=alt.Y("dataset:Q", title="Dataset"),
                    tooltip=["anno", "dataset"],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, width="stretch")
            n_max = real["anno"].max()
            n_avg = real.groupby("dataset").size().mean()
            st.info(f"📊 Copertura fino a **{n_max}** · media **{n_avg:.1f}** anni/dataset")

st.markdown("---")

# ── Verifica parquet ─────────────────────────────────────────────
st.subheader("Verifica parquet da GCS")
slug_options = [ds.get("slug", "") for ds in datasets if ds.get("period", {}).get("start")]
col_vs, col_vy, _ = st.columns([2, 1, 4])
with col_vs:
    verify_slug = st.selectbox("Dataset", slug_options, key="cat_verify_slug")
with col_vy:
    verify_year = st.number_input(
        "Anno", min_value=2010, max_value=2026, value=2023, step=1, key="cat_verify_year"
    )

if st.button("🔍 Verifica su GCS", key="cat_verify_btn"):
    with st.spinner(f"Verifica {verify_slug}/{verify_year}..."):
        try:
            result = verify_parquet(verify_slug, verify_year)
            if result["records"] >= 0:
                parquet_url = https_url(
                    "clean", "clean_parquet", slug=verify_slug, year=verify_year
                )
                st.success(f"✅ **{verify_slug}**/{verify_year} — **{result['records']:,}** record")
                st.markdown(
                    f"📥 **[Scarica parquet]({parquet_url})** — {result['records']:,} righe"
                )
            else:
                st.warning("⚠️ Parquet trovato ma 0 record")
        except Exception as e:
            st.error(f"❌ Parquet non raggiungibile: {e}")

data_freshness_note()
