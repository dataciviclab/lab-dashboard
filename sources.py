"""
Fonti dati condivise per il dashboard.
Legge da GitHub raw (metadati) e, opzionalmente, GCS parquet via DuckDB.

I path GCS seguono il path contract canonico definito in:
    lab-connectors/lab_connectors/gcs/paths.py  (paths.json)

I loader usano st.cache_data e mostrano errori con st.error() per robustezza
in produzione Streamlit. I fallback su dict/list vuoti evitano crash di pagina.
"""

import os
from datetime import datetime, timezone
from typing import Any, Optional

import duckdb
import pandas as pd
import requests
import streamlit as st
import yaml
from lab_connectors.gcs.paths import CLEAN_BUCKET, https_url
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGO_URL = "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg"

REGISTRY_BASE = "https://raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry"
SO_BASE = "https://raw.githubusercontent.com/dataciviclab/source-observatory/main"
GCS_BASE = f"https://storage.googleapis.com/{CLEAN_BUCKET}"


# ── Data fetching ─────────────────────────────────────────────────────────────────
_LAST_FETCH: dict[str, datetime] = {}


_HTTP = requests.Session()
_HTTP.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]),
    ),
)
_HTTP.mount(
    "http://",
    HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]),
    ),
)


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
        return _fetch_json(https_url("clean", "catalog_inventory_report"))
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
        inv_url = https_url("clean", "catalog_inventory_latest")
        chk_url = https_url("clean", "catalog_inventory_source_check")
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
    path = https_url("clean", "clean_parquet", slug=slug, year=year)
    with duckdb.connect() as con:
        df = con.sql("SELECT COUNT(*) AS records FROM read_parquet(?)", params=[path]).df()
    records = int(df["records"].iloc[0])
    return {"slug": slug, "year": year, "records": records}


# ── Explorer e Analisi (per pipeline end-to-end) ──────────────────────────────

DE_BASE = "https://raw.githubusercontent.com/dataciviclab/data-explorer/main/src/data"
DCL_BASE = "https://raw.githubusercontent.com/dataciviclab/dataciviclab/main/analisi"


@st.cache_data(ttl=3600, show_spinner=False)
def load_explorer_datasets() -> set[str]:
    """Dataset slug DE presenti su data-explorer.

    Scarica e fa il parse di ``themes.json.py`` usando ``ast.literal_eval``
    (sicuro: nessuna esecuzione di codice remoto). Restituisce l'insieme
    di tutti gli slug DE presenti negli themes.
    """
    import ast

    try:
        r = _HTTP.get(f"{DE_BASE}/themes.json.py", timeout=15)
        r.raise_for_status()
        # themes.json.py contiene anche ``json.dump(themes, ...)`` dopo l'array.
        # Usiamo AST per estrarre solo il nodo ``themes`` senza eseguire codice.
        module = ast.parse(r.text)
        themes = None
        for node in module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "themes":
                        themes = ast.literal_eval(node.value)
                        break
                if themes is not None:
                    break
        if themes is None:
            return set()
        slugs: set[str] = set()
        for t in themes:
            slugs.update(t.get("datasets", []))
        return slugs
    except Exception:
        # Fallback silenzioso: upstream irraggiungibile
        return set()


@st.cache_data(ttl=3600, show_spinner=False)
def load_analysis_registry() -> dict[str, str]:
    """Mappa slug analisi → slug dataset (da README frontmatter).

    Usa GitHub API per listare le directory in ``analisi/``, poi legge
    il ``dataset_slug`` dal frontmatter YAML di ogni README.md.
    Restituisce {analysis_slug: dataset_slug}.
    """
    try:
        r = _HTTP.get(
            "https://api.github.com/repos/dataciviclab/dataciviclab/contents/analisi",
            timeout=15,
        )
        r.raise_for_status()
        items = r.json()
    except Exception:
        # Fallback silenzioso: upstream irraggiungibile
        return {}

    registry: dict[str, str] = {}
    for item in items:
        if item["type"] != "dir":
            continue
        slug = item["name"]
        if slug in ("registry", "_template"):
            continue

        # Legge README.md e cerca dataset_slug nel frontmatter
        try:
            rr = _HTTP.get(f"{DCL_BASE}/{slug}/README.md", timeout=10)
            rr.raise_for_status()
            for line in rr.text.splitlines():
                if line.startswith("dataset_slug:"):
                    ds_slug = line.split(":", 1)[1].strip()
                    registry[slug] = ds_slug
                    break
        except Exception:
            pass

    return registry
