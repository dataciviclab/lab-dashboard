"""
Fonti dati condivise per il dashboard.
Legge da GitHub raw (metadati) e, opzionalmente, GCS parquet via DuckDB.

I loader usano st.cache_data e mostrano errori con st.error() per robustezza
in produzione Streamlit. I fallback su dict/list vuoti evitano crash di pagina.
"""
import os
from datetime import datetime, timezone
from typing import Any, Optional

import duckdb
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st
import yaml

LOGO_URL = "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg"

REGISTRY_BASE = "https://raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry"
SO_BASE = "https://raw.githubusercontent.com/dataciviclab/source-observatory/main"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"


# ── Data fetching ─────────────────────────────────────────────────────────────────
_LAST_FETCH: dict[str, datetime] = {}


_HTTP = requests.Session()
_HTTP.mount("https://", HTTPAdapter(
    max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]),
))
_HTTP.mount("http://", HTTPAdapter(
    max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]),
))


def _fetch_json(url: str) -> Any:
    """Fetch JSON. Solleva eccezioni — la UI gestisce l'errore."""
    r = _HTTP.get(url, timeout=15)
    r.raise_for_status()
    _LAST_FETCH[url] = datetime.now(timezone.utc)
    return r.json()


def _fetch_yaml(url: str) -> dict:
    """Fetch YAML. Solleva eccezioni — la UI gestisce l'errore."""
    r = _HTTP.get(url, timeout=15)
    r.raise_for_status()
    _LAST_FETCH[url] = datetime.now(timezone.utc)
    return yaml.safe_load(r.text) or {}


# ── Caricatori con cache — errori mostrati nella UI ──────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_catalog():
    try:
        return _fetch_json(f"{REGISTRY_BASE}/clean_catalog.json")
    except Exception as e:
        st.error(f"❌ Catalogo non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_signals():
    try:
        return _fetch_json(f"{REGISTRY_BASE}/pipeline_signals.json")
    except Exception as e:
        st.error(f"❌ Segnali pipeline non disponibili: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_radar():
    try:
        return _fetch_json(f"{SO_BASE}/data/radar/radar_summary.json")
    except Exception as e:
        st.error(f"❌ Radar fonti non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_sources_registry():
    try:
        return _fetch_yaml(f"{SO_BASE}/data/radar/sources_registry.yaml")
    except Exception as e:
        st.error(f"❌ Registro fonti non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_radar_history():
    """
    Storico probe radar: transizioni stato per fonte.
    Usato in 05_Radar.py per timeline chart.
    """
    try:
        return _fetch_json(f"{SO_BASE}/data/radar/radar_history.json")
    except Exception as e:
        st.error(f"❌ Storico radar non disponibile: {e}")
        return {"probes": []}


@st.cache_data(ttl=300, show_spinner=False)
def load_catalog_signals():
    """
    Segnali inventariali SO: metric_value, suggested_action, topics per fonte.
    Usato in 04_Funnel_Candidate per prioritizzare lo scouting.
    """
    try:
        return _fetch_json(f"{SO_BASE}/data/catalog/catalog_signals.json")
    except Exception as e:
        st.error(f"❌ Segnali catalogo non disponibili: {e}")
        return {"signals": []}


@st.cache_data(ttl=300, show_spinner=False)
def load_inventory_report():
    """
    Report inventario SO da GCS: stato build, righe, errore per fonte.
    Usato in 05_Radar.py e 07_Fonti.py per badge ✅/❌ e tabella fonti.
    """
    try:
        return _fetch_json(f"{GCS_BASE}/catalog_inventory/catalog_inventory_report.json")
    except Exception as e:
        st.error(f"❌ Report inventario non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_check_coverage():
    """
    Items in inventario vs items checked per fonte, via DuckDB su GCS parquet.
    Incrocia catalog_inventory_latest.parquet con source_check_results.parquet.
    Ritorna DataFrame con: source_id, inv_items, chk_items, reachable, candidates.
    """
    try:
        inv_url = f"{GCS_BASE}/catalog_inventory/catalog_inventory_latest.parquet"
        chk_url = f"{GCS_BASE}/catalog_inventory/source-check/source_check_results.parquet"
        with duckdb.connect() as con:
            return con.sql(f"""
                SELECT COALESCE(i.source_id, c.source_id) AS source_id,
                       COALESCE(i.inv_items, 0)::BIGINT AS inv_items,
                       COALESCE(c.chk_items, 0)::BIGINT AS chk_items,
                       COALESCE(c.reachable, 0)::BIGINT AS reachable,
                       COALESCE(c.candidates, 0)::BIGINT AS candidates
                FROM (SELECT source_id, COUNT(*) AS inv_items
                      FROM read_parquet('{inv_url}') GROUP BY source_id) i
                FULL JOIN (SELECT source_id,
                                  COUNT(*) AS chk_items,
                                  SUM(CASE WHEN reachable THEN 1 ELSE 0 END) AS reachable,
                                  SUM(CASE WHEN intake_candidate THEN 1 ELSE 0 END) AS candidates
                           FROM read_parquet('{chk_url}') GROUP BY source_id) c
                ON i.source_id = c.source_id
                ORDER BY inv_items DESC
            """).df()
    except Exception as e:
        st.error(f"❌ Check coverage non disponibile: {e}")
        return pd.DataFrame()


def last_fetch_time() -> Optional[datetime]:
    if not _LAST_FETCH:
        return None
    return max(_LAST_FETCH.values())


def data_freshness_note():
    """Mostra nota 'dati caricati al ...' nella pagina chiamante."""
    t = last_fetch_time()
    if t:
        st.caption(f"📡 Dati caricati: {t.strftime('%d/%m/%Y %H:%M')} UTC")


# ── GitHub Discussions ────────────────────────────────────────────────────────────
def _github_token():
    """Ritorna GITHUB_TOKEN da st.secrets o env. None se assente."""
    try:
        return st.secrets.get("github_token") or os.environ.get("GITHUB_TOKEN")
    except Exception:
        return os.environ.get("GITHUB_TOKEN")


@st.cache_data(ttl=300, show_spinner=False)
def load_recent_discussions(limit: int = 5):
    """
    Recupera le ultime discussion dal repo dataciviclab/dataciviclab.
    Usa GraphQL API. Se non c'è token, restituisce lista vuota.
    """
    token = _github_token()
    if not token:
        return []

    query = {
        "query": f"""{{ repository(owner: "dataciviclab", name: "dataciviclab") {{
            discussions(first: {limit}, orderBy: {{field: CREATED_AT, direction: DESC}}) {{
                totalCount
                nodes {{ title createdAt category {{ name }} url }}
            }}
        }} }}"""
    }

    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json=query,
            headers={"Authorization": f"bearer {token}"},
            timeout=10,
        )
        data = r.json()
        return data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
    except Exception:
        return []


def load_discussion_counts():
    """
    Ritorna conteggi per categoria: {'totale': N, 'domande': N, 'analisi': N, ...}
    """
    token = _github_token()
    if not token:
        return {"totale": 0, "domande": 0, "analisi": 0}

    query = {
        "query": """{
            repository(owner: "dataciviclab", name: "dataciviclab") {
                totale: discussions(first: 0) { totalCount }
            }
        }"""
    }

    try:
        r = requests.post(
            "https://api.github.com/graphql",
            json=query,
            headers={"Authorization": f"bearer {token}"},
            timeout=10,
        )
        data = r.json()
        total = data["data"]["repository"]["totale"]["totalCount"]
        return {"totale": total, "domande": "?", "analisi": "?"}
    except Exception:
        return {"totale": 0, "domande": 0, "analisi": 0}


# ── DuckDB (opzionale — attualmente usato solo per verifica spot) ────────────────
def duckdb_query(sql: str) -> pd.DataFrame:
    """Esegue SQL su DuckDB (in-memory). Chiude la connessione al termine."""
    with duckdb.connect() as con:
        return con.sql(sql).df()


def verify_parquet(slug: str, year: int) -> dict:
    """
    Verifica se un parquet GCS esiste e ha dati.
    Usa parametri DuckDB, non f-string, per evitare SQL injection.
    Ritorna {'slug': ..., 'year': ..., 'records': N} o solleva eccezione.
    """
    path = f"{GCS_BASE}/{slug}/{year}/{slug}_{year}_clean.parquet"
    with duckdb.connect() as con:
        df = con.sql("SELECT COUNT(*) AS records FROM read_parquet(?)", params=[path]).df()
    records = int(df["records"].iloc[0])
    return {"slug": slug, "year": year, "records": records}


def download_parquet_csv(slug: str, year: int, max_rows: int = 0) -> str:
    """
    Scarica un parquet da GCS e lo restituisce come stringa CSV.
    max_rows=0 = tutte le righe (attenzione: dataset grandi).
    Usa parametri DuckDB per evitare SQL injection.
    """
    path = f"{GCS_BASE}/{slug}/{year}/{slug}_{year}_clean.parquet"
    with duckdb.connect() as con:
        if max_rows > 0:
            df = con.sql("SELECT * FROM read_parquet(?) LIMIT ?", params=[path, max_rows]).df()
        else:
            df = con.sql("SELECT * FROM read_parquet(?)", params=[path]).df()
    return df.to_csv(index=False)
