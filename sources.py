"""
Fonti dati condivise per il dashboard.

Architettura:
  ACB (2 JSON) — catalogo, radar, segnali, discussions, PR, issues, analyses.
  SO direct (5 file) — radar history, source dashboard, source reports,
                        catalog signals, inventory report.
  GCS DuckDB — verify parquet.

I path GCS seguono il path contract canonico definito in:
    lab-connectors/lab_connectors/gcs/paths.py  (paths.json)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import duckdb
import requests
import streamlit as st
import yaml
from lab_connectors.gcs.paths import CLEAN_BUCKET, https_url
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGO_URL = "https://raw.githubusercontent.com/dataciviclab/lab-dashboard/main/static/logo.jpg"

# ── URLs ──────────────────────────────────────────────────────────────────────
ACB_BASE = "https://raw.githubusercontent.com/dataciviclab/agent-context-builder/context"
TOPIC_INDEX_URL = f"{ACB_BASE}/topic_index.json"
WORKSPACE_TRIAGE_URL = f"{ACB_BASE}/workspace_triage.json"
SO_BASE = "https://raw.githubusercontent.com/dataciviclab/source-observatory/main"
GCS_BASE = f"https://storage.googleapis.com/{CLEAN_BUCKET}"

# ── HTTP session ──────────────────────────────────────────────────────────────
_LAST_FETCH: dict[str, datetime] = {}

_HTTP = requests.Session()
_HTTP.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    ),
)
_HTTP.mount(
    "http://",
    HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    ),
)


def _fetch_json(url: str) -> Any:
    r = _HTTP.get(url, timeout=15)
    r.raise_for_status()
    _LAST_FETCH[url] = datetime.now(timezone.utc)
    return r.json()


def _fetch_yaml(url: str) -> dict:
    r = _HTTP.get(url, timeout=15)
    r.raise_for_status()
    _LAST_FETCH[url] = datetime.now(timezone.utc)
    return yaml.safe_load(r.text) or {}


# ══════════════════════════════════════════════════════════════════════════════
# ACB loaders
# ══════════════════════════════════════════════════════════════════════════════


@st.cache_data(ttl=300, show_spinner=False)
def load_topic_index() -> dict[str, Any]:
    try:
        return _fetch_json(TOPIC_INDEX_URL)
    except Exception as e:
        st.error(f"❌ Topic index non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_workspace_triage() -> dict[str, Any]:
    try:
        return _fetch_json(WORKSPACE_TRIAGE_URL)
    except Exception as e:
        st.error(f"❌ Workspace triage non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_catalog() -> dict[str, Any]:
    """Catalogo dataset — tutti i dataset da tutti i repo, con details."""
    ti = load_topic_index()
    all_datasets = []
    for source, ds_list in ti.get("datasets", {}).items():
        for ds in ds_list:
            entry = dict(ds)
            entry["source"] = source
            all_datasets.append(entry)
    return {"datasets": all_datasets}


@st.cache_data(ttl=300, show_spinner=False)
def load_signals() -> dict[str, Any]:
    """Segnali pipeline — da registry_summary.signals_detail."""
    triage = load_workspace_triage()
    signals = []
    for repo_info in triage.get("registry_summary", []):
        for sig in repo_info.get("signals_detail", []):
            entry = dict(sig)
            if "run" not in entry or entry["run"] is None:
                entry["run"] = {}
            signals.append(entry)
    return {
        "schema_version": "2",
        "signals": signals,
        "pipeline_state": triage.get("pipeline_state", {}),
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_radar() -> dict[str, Any]:
    """Radar fonti — 36 fonti da workspace_triage.radar."""
    triage = load_workspace_triage()
    radar = triage.get("radar", {})
    return {
        "generated_at": radar.get("generated_at", ""),
        "probe_date": radar.get("probe_date", ""),
        "sources_total": radar.get("sources_total", 0),
        "status_counts": {
            "GREEN": radar.get("green", 0),
            "YELLOW": radar.get("yellow", 0),
            "RED": radar.get("red", 0),
        },
        "persistent_red": radar.get("persistent_red", 0),
        "sources": radar.get("sources", []),
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_explorer_datasets() -> set[str]:
    """Dataset slug Explorer — da topic_index.explorer_themes."""
    ti = load_topic_index()
    slugs: set[str] = set()
    for t in ti.get("explorer_themes", []):
        slugs.update(t.get("datasets", []))
    return slugs


@st.cache_data(ttl=300, show_spinner=False)
def load_analyses() -> list[dict[str, Any]]:
    """Analisi pubblicate — da topic_index.analyses."""
    ti = load_topic_index()
    return ti.get("analyses", [])


@st.cache_data(ttl=300, show_spinner=False)
def load_operational_topics() -> dict[str, Any]:
    """Temi operativi (pipeline/governance/infrastructure) — da topic_index."""
    ti = load_topic_index()
    return ti.get("operational_topics", {})


@st.cache_data(ttl=300, show_spinner=False)
def load_source_health() -> dict[str, Any]:
    """Salute fonti: regressions + drift alerts — da workspace_triage.source_health."""
    triage = load_workspace_triage()
    return triage.get("source_health", {})


@st.cache_data(ttl=300, show_spinner=False)
def load_discussions() -> list[dict[str, Any]]:
    """Discussioni recenti — da workspace_triage.discussions."""
    triage = load_workspace_triage()
    return triage.get("discussions", [])[:15]


# ══════════════════════════════════════════════════════════════════════════════
# SO direct loaders
# ══════════════════════════════════════════════════════════════════════════════


@st.cache_data(ttl=300, show_spinner=False)
def load_radar_history() -> dict[str, Any]:
    try:
        return _fetch_json(f"{SO_BASE}/data/radar/radar_history.json")
    except Exception as e:
        st.error(f"❌ Radar history non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_sources_registry() -> dict[str, Any]:
    """Registro fonti — da SO sources_registry.yaml (per-source: protocol, observation_mode)."""
    try:
        return _fetch_yaml(f"{SO_BASE}/data/radar/sources_registry.yaml")
    except Exception as e:
        st.error(f"❌ Sources registry non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_sources_dashboard() -> dict[str, Any]:
    try:
        return _fetch_json(f"{SO_BASE}/data/reports/sources_dashboard.json")
    except Exception as e:
        st.error(f"❌ Sources dashboard non disponibile: {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_source_report(source_id: str) -> dict[str, Any]:
    try:
        return _fetch_json(f"{SO_BASE}/data/reports/source_reports/{source_id}.json")
    except Exception as e:
        st.error(f"❌ Source report non disponibile per '{source_id}': {e}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_catalog_signals() -> dict[str, Any]:
    """Segnali catalogo — da SO catalog_signals.json (per-source: result, metric_value)."""
    try:
        return _fetch_json(f"{SO_BASE}/data/catalog/catalog_signals.json")
    except Exception as e:
        st.error(f"❌ Catalog signals non disponibile: {e}")
        return {}


@st.cache_data(ttl=600, show_spinner=False)
def load_inventory_report() -> dict[str, Any]:
    try:
        return _fetch_json(f"{GCS_BASE}/catalog_inventory/catalog_inventory_report.json")
    except Exception as e:
        st.error(f"❌ Inventory report non disponibile: {e}")
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# GCS helpers
# ══════════════════════════════════════════════════════════════════════════════


def verify_parquet(slug: str, year: int) -> dict[str, Any]:
    path = https_url("clean", "clean_parquet", slug=slug, year=year)
    with duckdb.connect() as con:
        df = con.sql("SELECT COUNT(*) AS records FROM read_parquet(?)", params=[path]).df()
    return {"slug": slug, "year": year, "records": int(df["records"].iloc[0])}


# ── Utilities ─────────────────────────────────────────────────────────────────

DE_SLUG_MAP = {
    "aifa_spesa_consumo": "spesa-farmaceutica",
    "ispra_ru_base": "rifiuti-urbani",
    "civile_flussi": "flussi-giustizia-civile",
    "terna_capacita_rinnovabile": "capacita-rinnovabile",
    "terna_electricity_by_source": "produzione-elettrica-fonti",
    "bdap_entrate_stato": "entrate-stato",
    "inps_pensioni_trimestrale": "pensioni-inps",
}


def de_slug(di_slug: str) -> str:
    return DE_SLUG_MAP.get(di_slug, di_slug.replace("_", "-"))


def data_freshness_note() -> None:
    if _LAST_FETCH:
        t = max(_LAST_FETCH.values())
        st.caption(f"📡 Dati caricati: {t.strftime('%d/%m/%Y %H:%M')} UTC")
