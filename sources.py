"""
Fonti dati condivise per il dashboard.
Legge da GitHub raw (metadati) e, opzionalmente, GCS parquet via DuckDB.

Data layer puro: non chiama mai st.*. Le eccezioni vengono propagate
ai chiamanti che decidono come mostrare l'errore.
"""
import io
from datetime import datetime, timezone
from typing import Any, Optional

import duckdb
import pandas as pd
import requests
import streamlit as st
import yaml

LOGO_URL = "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg"

REGISTRY_BASE = "https://raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry"
SO_BASE = "https://raw.githubusercontent.com/dataciviclab/source-observatory/main"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"


# ── Sidebar comune (UI) ───────────────────────────────────────────────────────────
def render_sidebar_common():
    """Widget sidebar comuni a tutte le pagine."""
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


# ── Data fetching (puro, no st.*) ─────────────────────────────────────────────────
_LAST_FETCH: dict[str, datetime] = {}


def _fetch_json(url: str) -> Any:
    """Fetch JSON. Solleva eccezioni — la UI gestisce l'errore."""
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    _LAST_FETCH[url] = datetime.now(timezone.utc)
    return r.json()


def _fetch_yaml(url: str) -> dict:
    """Fetch YAML. Solleva eccezioni — la UI gestisce l'errore."""
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    _LAST_FETCH[url] = datetime.now(timezone.utc)
    return yaml.safe_load(r.text) or {}


# ── Caricatori con cache e decorator safe — la UI riceve fallback silenzioso ──────
def _safe(fn):
    """Wrapper: cattura eccezioni e restituisce valore di fallimento."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except requests.RequestException as e:
            st.error(f"❌ **{fn.__name__}**: {e}")
            return {}
        except Exception as e:
            st.error(f"❌ **{fn.__name__}**: errore imprevisto — {e}")
            return {}
    return wrapper


@st.cache_data(ttl=120, show_spinner=False)
@_safe
def load_catalog():
    return _fetch_json(f"{REGISTRY_BASE}/clean_catalog.json")


@st.cache_data(ttl=120, show_spinner=False)
@_safe
def load_signals():
    return _fetch_json(f"{REGISTRY_BASE}/pipeline_signals.json")


@st.cache_data(ttl=120, show_spinner=False)
@_safe
def load_radar():
    return _fetch_json(f"{SO_BASE}/data/radar/radar_summary.json")


@st.cache_data(ttl=120, show_spinner=False)
@_safe
def load_sources_registry():
    return _fetch_yaml(f"{SO_BASE}/data/radar/sources_registry.yaml")


def last_fetch_time() -> Optional[datetime]:
    if not _LAST_FETCH:
        return None
    return max(_LAST_FETCH.values())


def data_freshness_note():
    """Mostra nota 'dati caricati al ...' nella pagina chiamante."""
    t = last_fetch_time()
    if t:
        st.caption(f"📡 Dati caricati: {t.strftime('%d/%m/%Y %H:%M')} UTC")


# ── DuckDB (opzionale — attualmente usato solo per verifica spot) ────────────────
def duckdb_query(sql: str) -> pd.DataFrame:
    """Esegue SQL su DuckDB (in-memory). Solleva eccezioni."""
    con = duckdb.connect()
    return con.sql(sql).df()


def verify_parquet(slug: str, year: int) -> dict:
    """
    Verifica se un parquet GCS esiste e ha dati.
    Ritorna {'slug': ..., 'year': ..., 'records': N} o solleva eccezione.
    """
    path = f"{GCS_BASE}/{slug}/{year}/{slug}_{year}_clean.parquet"
    df = duckdb_query(f"SELECT COUNT(*) AS records FROM read_parquet('{path}')")
    records = int(df["records"].iloc[0])
    return {"slug": slug, "year": year, "records": records}
