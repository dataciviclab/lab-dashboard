"""
Test per sources.py — loader, fetching e fallback.
Non testa pagine Streamlit (troppo dipendenti dal runtime).

Contratto: i loader () producono dict/list strutturati da GitHub raw.
  _fetch_json/_fetch_yaml gestiscono successo/errore HTTP.
  I loader hanno fallback su dict/list vuoti quando HTTP fallisce.
  La serializzazione e' controllata da st.cache_data.

Prova del fuoco: se cancello questi test, un refactor di sources.py puo'
rompere tutti i 9 loader che alimentano il dashboard.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from sources import (
    _fetch_json,
    _fetch_yaml,
    _github_token,
    duckdb_query,
    load_analysis_registry,
    load_catalog,
    load_catalog_signals,
    load_explorer_datasets,
    load_inventory_report,
    load_radar,
    load_radar_history,
    load_signals,
    load_sources_registry,
    verify_parquet,
)

# ── Helpers ─────────────────────────────────────────────────────────────────


def _py_resp(source: str, status: int = 200) -> MagicMock:
    """Mock response per file Python (es. themes.json.py)."""
    m = MagicMock()
    m.status_code = status
    m.text = source
    if status >= 400:
        m.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        m.raise_for_status.return_value = None
    return m


def _resp(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.text = json.dumps(data)
    if status >= 400:
        m.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        m.raise_for_status.return_value = None
    return m


def _yaml_resp(text, status=200):
    m = MagicMock()
    m.status_code = status
    m.text = text
    if status >= 400:
        m.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        m.raise_for_status.return_value = None
    return m


# ── _fetch_json ─────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestFetchJson:
    URL = "https://example.com/data.json"

    def test_success(self):
        data = {"key": "value"}
        with patch("sources._HTTP.get", return_value=_resp(data)):
            assert _fetch_json(self.URL) == data

    def test_http_error(self):
        with patch("sources._HTTP.get", return_value=_resp({}, status=500)):
            with pytest.raises(Exception, match="HTTP 500"):
                _fetch_json(self.URL)


# ── _fetch_yaml ─────────────────────────────────────────────────────────────


@pytest.mark.contract
class TestFetchYaml:
    URL = "https://example.com/data.yaml"

    def test_success(self):
        yaml_text = "key: value\nnested:\n  sub: 42\n"
        expected = {"key": "value", "nested": {"sub": 42}}
        with patch("sources._HTTP.get", return_value=_yaml_resp(yaml_text)):
            assert _fetch_yaml(self.URL) == expected

    def test_http_error(self):
        with patch("sources._HTTP.get", return_value=_yaml_resp("", status=503)):
            with pytest.raises(Exception, match="HTTP 503"):
                _fetch_yaml(self.URL)


# ── Loader fallback ─────────────────────────────────────────────────────────


LOADERS = [
    ("load_radar", load_radar, {}),
    ("load_radar_history", load_radar_history, {"probes": []}),
    ("load_catalog_signals", load_catalog_signals, {"signals": []}),
    ("load_inventory_report", load_inventory_report, {}),
    ("load_catalog", load_catalog, {}),
    ("load_signals", load_signals, {}),
]


@pytest.mark.contract
@pytest.mark.parametrize("name,loader,expected_fallback", LOADERS)
def test_loader_fallback_on_http_error(name, loader, expected_fallback):
    """Ogni loader deve ritornare fallback quando HTTP fallisce (502)."""
    with patch("sources._HTTP.get", return_value=_resp({}, status=502)):
        result = loader()
    assert result == expected_fallback


# ── Loader risposta positiva ────────────────────────────────────────────────


RADAR_SAMPLE = {
    "sources_total": 23,
    "sources": [{"id": "istat_sdmx", "status": "GREEN", "protocol": "sdmx"}],
    "status_counts": {"GREEN": 18, "YELLOW": 4, "RED": 1},
}

RADAR_HISTORY_SAMPLE = {
    "probes": [{"probe_date": "2026-05-18", "sources": [{"id": "istat_sdmx", "status": "GREEN"}]}]
}

SIGNALS_SAMPLE = {
    "signals": [{"source": "aifa", "protocol": "html", "signal_type": "csv_magnet",
                  "metric_value": 42, "suggested_action": "catalog-watch-ready"}]
}

INVENTORY_SAMPLE = {"sources": {"istat_sdmx": {"status": "ok", "rows": 4849, "method": "dataflow_count"}}}

CATALOG_SAMPLE = {"datasets": [{"slug": "test", "stage": "published"}]}

PIPELINE_SAMPLE = {"signals": [{"id": "test", "status": "ok"}]}

REGISTRY_SAMPLE = """istat_sdmx:
  protocol: sdmx
  verdict: go
  observation_mode: catalog-watch
"""


@pytest.mark.contract
class TestLoaderSuccess:
    @patch("sources._HTTP.get", return_value=_resp(RADAR_SAMPLE))
    def test_load_radar(self, mock_get):
        result = load_radar()
        assert result["sources_total"] == 23

    @patch("sources._HTTP.get", return_value=_resp(RADAR_HISTORY_SAMPLE))
    def test_load_radar_history(self, mock_get):
        result = load_radar_history()
        assert len(result["probes"]) == 1

    @patch("sources._HTTP.get", return_value=_resp(SIGNALS_SAMPLE))
    def test_load_catalog_signals(self, mock_get):
        result = load_catalog_signals()
        assert len(result["signals"]) == 1

    @patch("sources._HTTP.get", return_value=_resp(INVENTORY_SAMPLE))
    def test_load_inventory_report(self, mock_get):
        result = load_inventory_report()
        assert result["sources"]["istat_sdmx"]["rows"] == 4849

    @patch("sources._HTTP.get", return_value=_resp(CATALOG_SAMPLE))
    def test_load_catalog(self, mock_get):
        result = load_catalog()
        assert len(result["datasets"]) == 1

    @patch("sources._HTTP.get", return_value=_resp(PIPELINE_SAMPLE))
    def test_load_signals(self, mock_get):
        result = load_signals()
        assert len(result["signals"]) == 1

    @patch("sources._HTTP.get", return_value=_yaml_resp(REGISTRY_SAMPLE))
    def test_load_sources_registry(self, mock_get):
        result = load_sources_registry()
        assert result["istat_sdmx"]["verdict"] == "go"


# ── _github_token ───────────────────────────────────────────────────────────


@pytest.mark.contract
class TestGithubToken:
    def test_from_secrets(self):
        with patch("sources.st.secrets", {"github_token": "tok-secret"}):
            with patch("sources.os.environ", {}):
                assert _github_token() == "tok-secret"

    def test_from_env(self):
        with patch("sources.st.secrets", {}):
            with patch("sources.os.environ", {"GITHUB_TOKEN": "tok-env"}):
                assert _github_token() == "tok-env"

    def test_secrets_overrides_env(self):
        with patch("sources.st.secrets", {"github_token": "tok-secret"}):
            with patch("sources.os.environ", {"GITHUB_TOKEN": "tok-env"}):
                assert _github_token() == "tok-secret"

    @pytest.mark.policy
    def test_returns_none_when_missing(self):
        """Senza token ne' in secrets ne' in env → None."""
        with patch("sources.st.secrets", {}):
            with patch("sources.os.environ", {}):
                assert _github_token() is None

    @pytest.mark.policy
    def test_handles_secrets_exception(self):
        """st.secrets puo' sollevare Exception (es. in ambiente senza secrets)."""
        with patch("sources.st.secrets") as mock_secrets:
            mock_secrets.get.side_effect = Exception("no secrets file")
            with patch("sources.os.environ", {"GITHUB_TOKEN": "tok-env"}):
                assert _github_token() == "tok-env"


# ── DuckDB functions ────────────────────────────────────────────────────────


class FakeDuckDB:
    """Simula duckdb.connect() per test."""

    class FakeResult:
        def df(self):
            import pandas as pd
            return pd.DataFrame({"records": [42]})

    class FakeConnection:
        def sql(self, query, params=None):
            return FakeDuckDB.FakeResult()
        def close(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    @staticmethod
    def connect():
        return FakeDuckDB.FakeConnection()


@pytest.mark.contract
class TestVerifyParquet:
    """Contratto: verify_parquet() verifica parquet GCS via DuckDB."""

    def test_returns_record_count(self):
        with patch("sources.duckdb.connect", FakeDuckDB.connect):
            result = verify_parquet("test-slug", 2023)
        assert result["slug"] == "test-slug"
        assert result["year"] == 2023
        assert result["records"] == 42

    def test_raises_on_error(self):
        with patch("sources.duckdb.connect") as mock_con:
            mock_con.return_value.__enter__.return_value.sql.side_effect = Exception("DuckDB error")
            with pytest.raises(Exception, match="DuckDB error"):
                verify_parquet("test-slug", 2023)


@pytest.mark.contract
class TestDuckdbQuery:
    """Contratto: duckdb_query() esegue SQL e restituisce DataFrame."""

    def test_executes_sql(self):
        fake_df = "fake_df"
        with patch("sources.duckdb.connect") as mock_con:
            mock_conn = MagicMock()
            mock_conn.__enter__.return_value.sql.return_value.df.return_value = fake_df
            mock_con.return_value = mock_conn
            result = duckdb_query("SELECT 1")
        assert result == fake_df


# ── Explorer + Analisi ────────────────────────────────────────────────────────

_THEMES_REALISTIC = """#!/usr/bin/env python3
import json, sys

themes = [
    {"slug": "territorio-ambiente",
     "datasets": ["rifiuti-urbani", "capacita-rinnovabile"]},
    {"slug": "finanza-pubblica",
     "datasets": ["irpef-comunale", "entrate-stato"]},
]

json.dump(themes, sys.stdout, ensure_ascii=False)
"""

_THEMES_SIMPLE = """themes = [
    {"slug": "a", "datasets": ["x", "y"]},
]"""


@pytest.mark.contract
class TestLoadExplorerDatasets:
    """Contratto: load_explorer_datasets() estrae slug da themes.json.py."""

    def test_parses_realistic_file_with_extra_code(self):
        """File realistico: ha ``json.dump(...)`` dopo l'array themes.

        Il vecchio parser (partition + literal_eval) falliva su questo caso
        perche' literal_eval non accetta codice extra dopo il literal.
        """
        with patch("sources._HTTP.get") as mock_get:
            mock_get.return_value = _py_resp(_THEMES_REALISTIC)
            result = load_explorer_datasets()
        assert result == {"rifiuti-urbani", "capacita-rinnovabile",
                          "irpef-comunale", "entrate-stato"}

    def test_parses_simple_file(self):
        """File minimale: solo l'assegnamento themes."""
        with patch("sources._HTTP.get") as mock_get:
            mock_get.return_value = _py_resp(_THEMES_SIMPLE)
            result = load_explorer_datasets()
        assert result == {"x", "y"}

    def test_returns_empty_on_http_error(self):
        with patch("sources._HTTP.get") as mock_get:
            mock_get.return_value = _py_resp("", status=500)
            result = load_explorer_datasets()
        assert result == set()


_ANALISI_README = """---
title: Test
dataset_slug: test_dataset
---
# Test analysis"""


@pytest.mark.contract
class TestLoadAnalysisRegistry:
    """Contratto: load_analysis_registry() mappa analisi → dataset_slug."""

    def test_parses_readme_frontmatter(self):
        gh_api_response = [
            {"type": "dir", "name": "test-analisi"},
            {"type": "dir", "name": "registry"},
            {"type": "file", "name": "README.md"},
        ]
        with patch("sources._HTTP.get") as mock_get:
            mock_get.side_effect = [
                _resp(gh_api_response),           # API directory listing
                _py_resp(_ANALISI_README),         # README.md
            ]
            result = load_analysis_registry()
        assert result == {"test-analisi": "test_dataset"}

    def test_skips_registry_and_template(self):
        gh_api_response = [
            {"type": "dir", "name": "registry"},
            {"type": "dir", "name": "_template"},
            {"type": "dir", "name": "irpef-comunale"},
        ]
        with patch("sources._HTTP.get") as mock_get:
            mock_get.side_effect = [
                _resp(gh_api_response),           # API listing
                _py_resp("---\ndataset_slug: irpef_comunale\n---"),  # README
            ]
            result = load_analysis_registry()
        assert "registry" not in result
        assert "_template" not in result
        assert result.get("irpef-comunale") == "irpef_comunale"

    def test_returns_empty_on_http_error(self):
        with patch("sources._HTTP.get") as mock_get:
            mock_get.return_value = _resp([], status=500)
            result = load_analysis_registry()
        assert result == {}
