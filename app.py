#!/usr/bin/env python3
"""
DataCivicLab · Dashboard operativo interno.
Pipeline health, candidate, copertura dataset, radar fonti.

Legge metadati da GitHub raw e dati reali da GCS parquet via DuckDB.
"""
import requests
import streamlit as st
import altair as alt
import pandas as pd
import duckdb

st.set_page_config(
    page_title="DataCivicLab · Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Fonti dati ─────────────────────────────────────────────────────────────────
REGISTRY_BASE = "https://raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"


@st.cache_data(ttl=120)
def load_json(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=120)
def load_catalog():
    return load_json(f"{REGISTRY_BASE}/clean_catalog.json")


@st.cache_data(ttl=120)
def load_signals():
    return load_json(f"{REGISTRY_BASE}/pipeline_signals.json")


def duckdb_query(sql):
    con = duckdb.connect()
    return con.sql(sql).df()


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.logo("https://raw.githubusercontent.com/dataciviclab/dataciviclab/main/assets/logo.svg")
st.sidebar.title("DataCivicLab")
st.sidebar.caption("Dashboard operativo")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Sezione",
    ["Vista d'insieme", "Dataset Explorer", "Pipeline Health", "Copertura dati"],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Dati: [dataset-incubator/registry](https://github.com/dataciviclab/dataset-incubator/tree/main/registry) · "
    "Clean parquet su GCS"
)

# ═══════════════════════════════════════════════════════════════════════════════
#  VISTA D'INSIEME
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Vista d'insieme":
    st.title("Vista d'insieme")

    catalog = load_catalog()
    signals = load_signals()

    datasets = catalog.get("datasets", [])
    sigs = signals.get("signals", [])
    sig_summary = signals.get("summary", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dataset", len(datasets))
    col2.metric("Pipeline OK", sig_summary.get("by_status", {}).get("ok", 0))
    col3.metric("Warning", sig_summary.get("by_status", {}).get("warn", 0))
    col4.metric("Errori", sig_summary.get("by_status", {}).get("error", 0))

    st.markdown("---")

    # Dataset per stage
    stage_counts = {}
    for ds in datasets:
        s = ds.get("stage", "unknown")
        stage_counts[s] = stage_counts.get(s, 0) + 1

    stage_df = pd.DataFrame([
        {"stage": s.capitalize(), "count": c}
        for s, c in sorted(stage_counts.items())
    ])

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Dataset per stage")
        st.bar_chart(stage_df.set_index("stage"))
        st.caption(f"Ultimo aggiornamento: {catalog.get('updated_at', '?')}")

    with col_b:
        st.subheader("Ultimi aggiornamenti")
        recent = sorted(
            datasets, key=lambda d: d.get("updated_at", ""), reverse=True
        )[:10]
        for ds in recent:
            st.write(f"- **{ds.get('slug', '?')}** · {ds.get('stage', '?')}")

    st.markdown("---")

    # Temi
    st.subheader("Dataset per tema")
    theme_counts = {}
    for ds in datasets:
        for t in ds.get("themes", []):
            theme_counts[t] = theme_counts.get(t, 0) + 1
    if theme_counts:
        theme_df = pd.DataFrame([
            {"tema": t, "count": c}
            for t, c in sorted(theme_counts.items(), key=lambda x: -x[1])
        ])
        st.bar_chart(theme_df.set_index("tema"))

# ═══════════════════════════════════════════════════════════════════════════════
#  DATASET EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Dataset Explorer":
    st.title("Dataset Explorer")

    catalog = load_catalog()
    datasets = catalog.get("datasets", [])

    stages = sorted(set(d.get("stage", "unknown") for d in datasets))
    stage_filter = st.selectbox("Filtra per stage", ["Tutti"] + stages)

    search = st.text_input("Cerca dataset", placeholder="slug o descrizione...")

    filtered = datasets
    if stage_filter != "Tutti":
        filtered = [d for d in filtered if d.get("stage") == stage_filter]
    if search:
        filtered = [
            d
            for d in filtered
            if search.lower() in d.get("slug", "").lower()
            or search.lower() in d.get("description", "").lower()
        ]

    st.write(f"**{len(filtered)} dataset** trovati")

    for ds in filtered:
        with st.expander(f"**{ds.get('slug', '?')}** — {ds.get('stage', '?')}"):
            st.write(f"**Descrizione:** {ds.get('description', '—')}")
            st.write(f"**Fonte:** {ds.get('source', '?')}")
            st.write(f"**Anni:** {ds.get('year_range', '?')}")
            if ds.get("url"):
                st.write(f"**URL:** {ds['url']}")
            if ds.get("discussion_url"):
                st.write(f"**Discussione:** {ds['discussion_url']}")

# ═══════════════════════════════════════════════════════════════════════════════
#  PIPELINE HEALTH
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Pipeline Health":
    st.title("Pipeline Health")

    signals = load_signals()
    sigs = signals.get("signals", [])

    ok_count = sum(1 for s in sigs if s.get("status") == "ok")
    warn_count = sum(1 for s in sigs if s.get("status") == "warn")
    err_count = sum(1 for s in sigs if s.get("status") == "error")

    col1, col2, col3 = st.columns(3)
    col1.metric("OK", ok_count)
    col2.metric("Warning", warn_count)
    col3.metric("Errori", err_count)

    st.markdown("---")

    st.subheader("Distribuzione")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        status_df = pd.DataFrame([
            {"status": "OK", "count": ok_count},
            {"status": "Warning", "count": warn_count},
            {"status": "Error", "count": err_count},
        ])
        pie = alt.Chart(status_df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="count", type="quantitative"),
            color=alt.Color(
                field="status",
                type="nominal",
                scale={
                    "domain": ["OK", "Warning", "Error"],
                    "range": ["#16a34a", "#fbbf24", "#dc2626"],
                },
            ),
            tooltip=["status", "count"],
        ).properties(width=300, height=300)
        st.altair_chart(pie)

    with col_b:
        st.subheader("Segnali")
        for sig in sigs:
            emoji = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(
                sig.get("status", ""), "❓"
            )
            st.write(f"{emoji} **{sig.get('label', '?')}** — {sig.get('detail', '')}")

# ═══════════════════════════════════════════════════════════════════════════════
#  COPERTURA DATI
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Copertura dati":
    st.title("Copertura dati")

    catalog = load_catalog()
    datasets = catalog.get("datasets", [])

    st.markdown(
        "Record per dataset/anno letti live dai parquet su GCS via DuckDB."
    )

    YEARS = list(range(2019, 2026))

    if st.button("Carica copertura live da GCS"):
        with st.spinner("Caricamento dati da GCS..."):
            rows = []
            for ds in datasets[:15]:  # limit to 15 for demo
                slug = ds.get("slug", "")
                source = catalog.get("sources", {}).get(slug)
                if not source:
                    continue
                col_anno = source.get("year_column", "anno")
                for y in YEARS:
                    path = f"{GCS_BASE}/{slug}/{y}/{slug}_{y}_clean.parquet"
                    try:
                        sql = f"SELECT '{slug}' AS dataset, {y} AS anno, COUNT(*) AS records FROM read_parquet('{path}')"
                        df = duckdb_query(sql)
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
