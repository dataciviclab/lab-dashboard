"""
Test per sources.py — loader, fetching e fallback.
Non testa pagine Streamlit (troppo dipendenti dal runtime).
"""
import json
from unittest.mock import patch, MagicMock

import pytest

# Neutralizza st.cache_data prima che sources.py lo usi,
# altrimenti il caching persiste tra test nello stesso processo.
import streamlit as st
st.cache_data = lambda **kwargs: lambda f: f
st.error = lambda msg: None

from sources import (  # noqa: E402  — mock st.cache_data prima dell'import
    _fetch_json,
    _fetch_yaml,
    load_catalog,
    load_catalog_signals,
    load_inventory_report,
    load_radar,
    load_radar_history,
    load_signals,
    load_sources_registry,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _resp(data, status=200):
    """Crea una mock response requests con dati JSON."""
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.text = json.dumps(data)
    if status >= 400:
        m.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        m.raise_for_status.return_value = None
    return m


def _yaml_resp(text: str, status=200):
    """Crea una mock response requests con testo YAML."""
    m = MagicMock()
    m.status_code = status
    m.text = text
    if status >= 400:
        m.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        m.raise_for_status.return_value = None
    return m


# ── _fetch_json ─────────────────────────────────────────────────────────────


class TestFetchJson:
    URL = "https://example.com/data.json"

    def test_success(self):
        """Fetch JSON con successo ritorna il dato parsato."""
        data = {"key": "value"}
        with patch("sources._HTTP.get", return_value=_resp(data)):
            assert _fetch_json(self.URL) == data

    def test_http_error(self):
        """Fetch JSON con errore HTTP solleva eccezione."""
        with patch("sources._HTTP.get", return_value=_resp({}, status=500)):
            with pytest.raises(Exception, match="HTTP 500"):
                _fetch_json(self.URL)


# ── _fetch_yaml ─────────────────────────────────────────────────────────────


class TestFetchYaml:
    URL = "https://example.com/data.yaml"

    def test_success(self):
        """Fetch YAML con successo ritorna dict parsato."""
        yaml_text = "key: value\nnested:\n  sub: 42\n"
        expected = {"key": "value", "nested": {"sub": 42}}
        with patch("sources._HTTP.get", return_value=_yaml_resp(yaml_text)):
            assert _fetch_yaml(self.URL) == expected

    def test_http_error(self):
        """Fetch YAML con errore HTTP solleva eccezione."""
        with patch("sources._HTTP.get", return_value=_yaml_resp("", status=503)):
            with pytest.raises(Exception, match="HTTP 503"):
                _fetch_yaml(self.URL)


# ── Loader fallback (errore HTTP → dict/list vuoto) ─────────────────────────


LOADERS = [
    ("load_radar", load_radar, {}),
    ("load_radar_history", load_radar_history, {"probes": []}),
    ("load_catalog_signals", load_catalog_signals, {"signals": []}),
    ("load_inventory_report", load_inventory_report, {}),
    ("load_catalog", load_catalog, {}),
    ("load_signals", load_signals, {}),
]


@pytest.mark.parametrize("name,loader,expected_fallback", LOADERS)
def test_loader_fallback_on_http_error(name, loader, expected_fallback):
    """Ogni loader deve ritornare fallback quando HTTP fallisce (502)."""
    with patch("sources._HTTP.get", return_value=_resp({}, status=502)):
        result = loader()
    assert result == expected_fallback, (
        f"{name}: expected {expected_fallback}, got {result}"
    )


# ── Loader risposta positiva ────────────────────────────────────────────────


RADAR_SAMPLE = {
    "sources_total": 23,
    "sources": [{"id": "istat_sdmx", "status": "GREEN", "protocol": "sdmx"}],
    "status_counts": {"GREEN": 18, "YELLOW": 4, "RED": 1},
}

RADAR_HISTORY_SAMPLE = {
    "probes": [
        {
            "probe_date": "2026-05-18",
            "sources": [{"id": "istat_sdmx", "status": "GREEN"}],
        }
    ]
}

SIGNALS_SAMPLE = {
    "signals": [
        {
            "source": "aifa",
            "protocol": "html",
            "signal_type": "csv_magnet",
            "metric_value": 42,
            "suggested_action": "catalog-watch-ready",
        }
    ]
}

INVENTORY_SAMPLE = {
    "sources": {
        "istat_sdmx": {
            "status": "ok", "rows": 4849, "method": "dataflow_count"
        }
    }
}

CATALOG_SAMPLE = {"datasets": [{"slug": "test", "stage": "published"}]}

PIPELINE_SAMPLE = {"signals": [{"id": "test", "status": "ok"}]}

REGISTRY_SAMPLE = """istat_sdmx:
  protocol: sdmx
  verdict: go
  observation_mode: catalog-watch
"""


class TestLoaderSuccess:
    @patch("sources._HTTP.get", return_value=_resp(RADAR_SAMPLE))
    def test_load_radar(self, mock_get):
        result = load_radar()
        assert result["sources_total"] == 23
        assert result["status_counts"]["GREEN"] == 18

    @patch("sources._HTTP.get", return_value=_resp(RADAR_HISTORY_SAMPLE))
    def test_load_radar_history(self, mock_get):
        result = load_radar_history()
        assert len(result["probes"]) == 1
        assert result["probes"][0]["probe_date"] == "2026-05-18"

    @patch("sources._HTTP.get", return_value=_resp(SIGNALS_SAMPLE))
    def test_load_catalog_signals(self, mock_get):
        result = load_catalog_signals()
        assert len(result["signals"]) == 1
        assert result["signals"][0]["source"] == "aifa"

    @patch("sources._HTTP.get", return_value=_resp(INVENTORY_SAMPLE))
    def test_load_inventory_report(self, mock_get):
        result = load_inventory_report()
        assert "istat_sdmx" in result["sources"]
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
        assert "istat_sdmx" in result
        assert result["istat_sdmx"]["verdict"] == "go"
