"""
Fonti dati condivise per il dashboard.
Legge da GitHub raw (metadati) e GCS parquet via DuckDB (dati vivi).

Tutte le fetch hanno try/except: se GitHub è giù, il dashboard non crasha
ma mostra un messaggio "dati non disponibili".
"""
import io
from datetime import datetime, timezone

import requests
import duckdb
import pandas as pd
import streamlit as st
import yaml

LOGO_URL = "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg"

REGISTRY_BASE = "https://raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry"
SO_BASE = "https://raw.githubusercontent.com/dataciviclab/source-observatory/main"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"


# ── Sidebar comune ────────────────────────────────────────────────────────────────
def render_sidebar_common():
    """Widget sidebar comuni a tutte le pagine.
    Include logo, auto-refresh, hint tema e footer.
    """
    # Logo — richiamato su ogni pagina per garantirne la visibilità
    st.logo(LOGO_URL, size="large")

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
    st.sidebar.markdown("---")
    st.sidebar.caption("🌙 **Tema scuro**: ☰ → Settings → Theme")
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "📦 [dataset-incubator/registry]"
        "(https://github.com/dataciviclab/dataset-incubator/tree/main/registry)"
    )


# ── Fetch con error handling ───────────────────────────────────────────────────────
_LAST_FETCH = {}  # tracciamento freschezza dati


def _fetch_json(url, label="dati"):
    """Fetch JSON con fallimento gracevole."""
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        _LAST_FETCH[url] = datetime.now(timezone.utc)
        return r.json()
    except requests.RequestException as e:
        st.error(f"❌ **{label}** non disponibile: {e}")
        return {}


def _fetch_yaml(url, label="dati"):
    """Fetch YAML con fallimento gracevole."""
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        _LAST_FETCH[url] = datetime.now(timezone.utc)
        return yaml.safe_load(r.text) or {}
    except requests.RequestException as e:
        st.error(f"❌ **{label}** non disponibile: {e}")
        return {}


# ── Caricatori specifici con cache ────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def load_catalog():
    return _fetch_json(f"{REGISTRY_BASE}/clean_catalog.json", "Catalogo dataset")


@st.cache_data(ttl=120, show_spinner=False)
def load_signals():
    return _fetch_json(f"{REGISTRY_BASE}/pipeline_signals.json", "Segnali pipeline")


@st.cache_data(ttl=120, show_spinner=False)
def load_radar():
    return _fetch_json(f"{SO_BASE}/data/radar/radar_summary.json", "Radar fonti")


@st.cache_data(ttl=120, show_spinner=False)
def load_sources_registry():
    return _fetch_yaml(f"{SO_BASE}/data/radar/sources_registry.yaml", "Registro fonti")


def last_fetch_time():
    """Ritorna il timestamp del fetch più recente, o None."""
    if not _LAST_FETCH:
        return None
    return max(_LAST_FETCH.values())


def data_freshness_note():
    """Stampa una nota 'dati aggiornati al ...'."""
    t = last_fetch_time()
    if t:
        st.caption(f"📡 Dati caricati: {t.strftime('%d/%m/%Y %H:%M')} UTC")
    else:
        st.caption("📡 Dati non ancora caricati")


# ── DuckDB ─────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def duckdb_query(sql):
    try:
        con = duckdb.connect()
        return con.sql(sql).df()
    except Exception as e:
        st.error(f"❌ Errore query DuckDB: {e}")
        return pd.DataFrame()


def get_dataset_years(slug: str):
    """
    Ritorna la lista degli anni disponibili per un dataset.
    Legge da catalog prima, poi prova GCS se serve.
    """
    cat = load_catalog()
    for ds in cat.get("datasets", []):
        if ds["slug"] == slug:
            yr = ds.get("period", {})
            start = yr.get("start")
            end = yr.get("end")
            if start and end:
                return list(range(start, end + 1))
    # fallback: anni tipici
    return list(range(2019, 2026))
