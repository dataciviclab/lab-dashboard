"""Query SQL interattiva sui dataset pubblici del DataCivicLab.

L'utente seleziona un dataset, scrive SQL su ``clean_input``, e ottiene risultati
in tempo reale via DuckDB che legge i Parquet su GCS — niente download, niente
pre-processing. Stesso pattern di clean-query-mcp: la CTE viene risolta
automaticamente sugli URL GCS per tutti gli anni del dataset.
"""
from __future__ import annotations

import time
from typing import Any

import duckdb
import pandas as pd
import streamlit as st
from lab_connectors.gcs.paths import https_url

from sources import data_freshness_note, load_catalog

st.title("🧪 Query SQL")
st.markdown(
    "Scrivi query **SQL** sui dataset pubblici. "
    "Usa ``clean_input`` come nome della tabella virtuale — "
    "viene risolta automaticamente sui **Parquet GCS** per tutti gli anni "
    "del dataset selezionato."
)

# ── Helper (cached) ─────────────────────────────────────────────────────────


@st.cache_data(ttl=60, show_spinner=False)
def _resolve_slug(slug: str) -> tuple[list[str], str, dict[str, Any]]:
    """Risolve slug → (urls, cte_expr, dataset_info).

    Gestisce due pattern dal catalogo:
    - ``multi_file=True``: un Parquet per anno → lista URL per tutti gli anni
    - ``multi_file=False``: un unico file multi-anno → URL dal path del catalogo

    La CTE expression è pronta per essere usata in:
        WITH clean_input AS ({cte_expr}) SELECT ...
    """
    catalog = load_catalog()
    for ds in catalog.get("datasets", []):
        if ds["slug"] == slug:
            loc = ds.get("location", {})
            multi = loc.get("multi_file", True)

            if multi:
                # Un Parquet per anno: costruisce URL per ogni anno
                period = ds.get("period", {})
                start = period.get("start")
                end = period.get("end")
                if not start or not end:
                    raise ValueError(
                        f"Periodo non definito per '{slug}' nel catalogo"
                    )
                years = list(range(start, end + 1))
                urls = [
                    https_url("clean", "clean_parquet", slug=slug, year=y)
                    for y in years
                ]
            else:
                # Singolo file multi-anno: prende il path dal catalogo
                gcs_path = loc.get("path", "")
                if not gcs_path:
                    raise ValueError(
                        f"Path non definito per '{slug}' nel catalogo"
                    )
                # Converte gs://BUCKET/PATH → https://storage.googleapis.com/BUCKET/PATH
                https_path = gcs_path.replace(
                    "gs://", "https://storage.googleapis.com/", 1
                )
                urls = [https_path]

            if len(urls) == 1:
                cte_expr = f"SELECT * FROM read_parquet('{urls[0]}')"
            else:
                paths = "', '".join(urls)
                cte_expr = f"SELECT * FROM read_parquet(['{paths}'])"

            return urls, cte_expr, ds

    raise ValueError(f"Dataset '{slug}' non trovato nel catalogo")


@st.cache_data(ttl=300, show_spinner=False)
def _get_schema_df(slug: str) -> pd.DataFrame:
    """Schema colonne: da catalogo (se presente) o fallback via DESCRIBE."""
    catalog = load_catalog()
    for ds in catalog.get("datasets", []):
        if ds["slug"] == slug:
            cols = ds.get("columns", [])
            if cols:
                return pd.DataFrame(
                    [
                        {
                            "colonna": c.get("name", "?"),
                            "tipo": c.get("type", "?"),
                            "ruolo": c.get("role", "?"),
                            "descrizione": c.get("description", ""),
                        }
                        for c in cols
                    ]
                )
            # Fallback: DESCRIBE dal primo parquet disponibile
            try:
                urls, _, _ = _resolve_slug(slug)
                if urls:
                    with duckdb.connect() as con:
                        return con.sql(
                            f"DESCRIBE SELECT * FROM read_parquet('{urls[0]}')"
                        ).df()
            except Exception:
                pass
            return pd.DataFrame()
    return pd.DataFrame()


def _build_query(user_sql: str, cte_expr: str, max_rows: int) -> str:
    """Avvolge la SQL utente nella CTE e applica il LIMIT."""
    return (
        f"WITH clean_input AS ({cte_expr}) "
        f"SELECT * FROM ({user_sql}) AS _q LIMIT {max_rows}"
    )


def _default_sql(ds: dict[str, Any]) -> str:
    """Query di esempio per il dataset selezionato."""
    period = ds.get("period", {})
    start = period.get("start", "?")
    end = period.get("end", "?")
    name = ds.get("name", ds.get("slug", ""))
    cols = ds.get("columns", [])
    col_hint = ""
    if cols:
        names = [c["name"] for c in cols[:5]]
        col_hint = f"-- Colonne: {', '.join(names)}..."
    return (
        f"-- Dataset: {name}\n"
        f"-- Periodo: {start}–{end}\n"
        f"{col_hint}\n"
        f"-- Usa clean_input come tabella virtuale\n"
        f"SELECT * FROM clean_input LIMIT 10"
    )


# ── Carica catalogo ─────────────────────────────────────────────────────────

catalog = load_catalog()
datasets: list[dict[str, Any]] = catalog.get("datasets", [])

if not datasets:
    st.error("Catalogo non disponibile. Verifica connessione a GitHub.")
    st.stop()

slug_options = sorted(d["slug"] for d in datasets)
default_idx = (
    slug_options.index("irpef_comunale")
    if "irpef_comunale" in slug_options
    else 0
)

# ── Toolbar: dataset e info ─────────────────────────────────────────────────

col_sel, col_actions = st.columns([2, 3])

with col_sel:
    selected_slug = st.selectbox(
        "Dataset",
        slug_options,
        index=default_idx,
        key="sql_query_slug",
    )

ds_info = next((d for d in datasets if d["slug"] == selected_slug), None)
if not ds_info:
    st.stop()

with col_actions:
    st.markdown("")  # spacing
    st.markdown("")  # spacing
    info_cols = st.columns([1, 1, 1])
    with info_cols[0]:
        period = ds_info.get("period", {})
        st.markdown(
            f"**Anni:** {period.get('start', '?')}–{period.get('end', '?')}"
        )
    with info_cols[1]:
        st.markdown(f"**Stage:** {ds_info.get('stage', '—')}")
    with info_cols[2]:
        st.markdown(f"**Slug:** ``{selected_slug}``")

# Schema + Info in expander compatti
exp_cols = st.columns([1, 1])
with exp_cols[0]:
    schema_df = _get_schema_df(selected_slug)
    if not schema_df.empty:
        with st.expander("Schema colonne", expanded=False):
            st.dataframe(
                schema_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "colonna": "Colonna",
                    "tipo": "Tipo",
                    "ruolo": "Ruolo",
                    "descrizione": st.column_config.TextColumn(
                        "Descrizione", width="large"
                    ),
                },
            )
with exp_cols[1]:
    desc = ds_info.get("description", "")
    source = ds_info.get("source", "")
    if desc or source:
        with st.expander("Info dataset", expanded=False):
            if desc:
                st.markdown(f"**Descrizione:** {desc}")
            if source:
                st.markdown(f"**Fonte:** {source}")

# ── Editor SQL ──────────────────────────────────────────────────────────────

default_sql = _default_sql(ds_info)
sql = st.text_area(
    "Scrivi la query SQL",
    value=st.session_state.get("sql_query_sql", default_sql),
    height=180,
    key="sql_query_input",
    placeholder="SELECT * FROM clean_input LIMIT 10",
    help=(
        "Usa clean_input come tabella virtuale.\n"
        "WHERE, GROUP BY, ORDER BY, JOIN funzionano.\n"
        "Per JOIN tra dataset usa read_parquet('url') diretto."
    ),
)

# Opzioni esecuzione
col_max, col_btn, _ = st.columns([1, 1, 5])
with col_max:
    max_rows = st.number_input(
        "Max righe",
        min_value=1,
        max_value=50_000,
        value=1_000,
        step=100,
    )
with col_btn:
    execute = st.button(":material/play_arrow: Esegui", type="primary")
    reset = st.button(":material/refresh: Reset", type="secondary")

if reset:
    st.session_state.sql_query_sql = _default_sql(ds_info)
    st.rerun()

# ── Storico query (prima dei risultati) ─────────────────────────────────────

if "sql_history" not in st.session_state:
    st.session_state.sql_history = []

if st.session_state.sql_history:
    with st.expander("Storico query", expanded=False):
        for i, entry in enumerate(st.session_state.sql_history[-8:]):
            label = entry["sql"][:60].replace("\n", " ")
            if len(entry["sql"]) > 60:
                label += "…"
            col_a, col_b = st.columns([6, 1])
            with col_a:
                if st.button(
                    f"`{entry['slug']}` {label}",
                    key=f"hist_{i}",
                    help=f"{entry['rows']} righe · {entry['time']}",
                ):
                    st.session_state.sql_query_sql = entry["sql"]
                    st.rerun()
            with col_b:
                st.caption(f"{entry['rows']} rows")
        if st.button("Svuota storico", key="clear_hist"):
            st.session_state.sql_history = []
            st.rerun()

# ── Esecuzione query ────────────────────────────────────────────────────────

if execute:
    st.session_state.sql_query_sql = sql

    with st.spinner(f"Esecuzione su `{selected_slug}` via DuckDB…"):
        try:
            # Risolvi slug → URL GCS
            urls, cte_expr, _ = _resolve_slug(selected_slug)
            wrapped_sql = _build_query(sql, cte_expr, max_rows)

            # Esegui
            t0 = time.perf_counter()
            with duckdb.connect() as con:
                df = con.sql(wrapped_sql).df()
            elapsed = time.perf_counter() - t0

            n_rows = len(df)
            is_truncated = n_rows >= max_rows

            # Metriche
            m1, m2, m3 = st.columns(3)
            m1.metric("Righe restituite", f"{n_rows:,}")
            m2.metric("Tempo esecuzione", f"{elapsed:.2f}s")
            file_label = "1 file" if len(urls) == 1 else f"{len(urls)} file"
            m3.metric("Parquet letti", file_label)

            if is_truncated:
                st.info(
                    f"Risultato troncato a {max_rows} righe. "
                    "Aumenta il limite o aggiungi ``LIMIT`` nella query."
                )

            if n_rows == 0 and not is_truncated:
                st.success(
                    "Query eseguita correttamente — **0 righe** restituite."
                )
            elif n_rows > 0:
                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        col: st.column_config.Column(col, width="medium")
                        for col in df.columns[:8]
                    },
                )

                # Download CSV
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    ":material/download: Scarica CSV",
                    data=csv_data,
                    file_name=f"{selected_slug}_query_{int(time.time())}.csv",
                    mime="text/csv",
                )

            # Storico
            st.session_state.sql_history.append(
                {
                    "slug": selected_slug,
                    "sql": sql,
                    "rows": n_rows,
                    "time": f"{elapsed:.2f}s",
                }
            )

            # SQL eseguita in expander (debug)
            with st.expander("SQL effettivamente eseguita", expanded=False):
                st.code(wrapped_sql, language="sql")

        except Exception as e:
            st.error(f"Errore durante l'esecuzione: {e}")
            if "wrapped_sql" in locals():
                with st.expander(
                    "SQL che ha causato l'errore", expanded=True
                ):
                    st.code(wrapped_sql, language="sql")

data_freshness_note()
