"""
Fonti dati condivise per il dashboard.
Legge da GitHub raw (metadati) e GCS parquet via DuckDB (dati vivi).
"""
import io

import requests
import duckdb
import pandas as pd
import streamlit as st
import yaml

LOGO_URL = "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg"


def render_sidebar_common():
    """Widget sidebar comuni a tutte le pagine (logo, auto-refresh, theme hint)."""
    # Auto-refresh toggle persistente tramite session_state
    refresh = st.sidebar.toggle(
        "🔄 Ricarica 60s",
        value=st.session_state.get("autorefresh", False),
        key="ar_global",
    )
    st.session_state.autorefresh = refresh
    if refresh:
        st.markdown(
            '<meta http-equiv="refresh" content="60">',
            unsafe_allow_html=True,
        )

    # Hint tema (Settings menu)
    st.sidebar.markdown("---")
    st.sidebar.caption("🌙 **Tema scuro**: ☰ → Settings → Theme")

    # Footer dati
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "📦 [dataset-incubator/registry]"
        "(https://github.com/dataciviclab/dataset-incubator/tree/main/registry)"
    )

# ── URL costanti ──────────────────────────────────────────────────────────────
REGISTRY_BASE = "https://raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry"
SO_BASE = "https://raw.githubusercontent.com/dataciviclab/source-observatory/main"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"


# ── Fetch helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner="Caricamento catalogo...")
def load_json(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=120, show_spinner="Caricamento fonti...")
def load_yaml(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return yaml.safe_load(r.text)


# ── Caricatori specifici ──────────────────────────────────────────────────────
def load_catalog():
    return load_json(f"{REGISTRY_BASE}/clean_catalog.json")


def load_signals():
    return load_json(f"{REGISTRY_BASE}/pipeline_signals.json")


def load_radar():
    return load_json(f"{SO_BASE}/data/radar/radar_summary.json")


def load_sources_registry():
    return load_yaml(f"{SO_BASE}/data/radar/sources_registry.yaml")


# ── DuckDB ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def duckdb_query(sql):
    con = duckdb.connect()
    return con.sql(sql).df()


def count_parquet(slug: str, year: int) -> int:
    """Conta record in un parquet GCS. Ritorna -1 se irraggiungibile."""
    path = f"{GCS_BASE}/{slug}/{year}/{slug}_{year}_clean.parquet"
    try:
        df = duckdb_query(
            f"SELECT COUNT(*) AS cnt FROM read_parquet('{path}')"
        )
        return int(df["cnt"].iloc[0])
    except Exception:
        return -1
