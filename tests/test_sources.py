"""
Test per sources.py — loader ACB-based e SO-direct.

Contratto: i loader ACB producono dict/list strutturati da topic_index.json
  e workspace_triage.json. I fallback su dict/list vuoti quando fetch fallisce.
  I loader SO diretti mantengono il comportamento legacy.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from sources import (
    _fetch_json,
    _fetch_yaml,
    de_slug,
    load_analyses,
    load_catalog,
    load_catalog_signals,
    load_explorer_datasets,
    load_operational_topics,
    load_radar,
    load_signals,
    load_source_health,
    load_sources_registry,
)

# ── Mock data ─────────────────────────────────────────────────────────────────

_MOCK_TOPIC_INDEX = {
    "schema_version": 4,
    "generated_at": "2026-08-27T10:00:00",
    "repos": {
        "dataciviclab": {
            "description": "Hub",
            "url": "https://github.com/dataciviclab/dataciviclab",
        },
        "dataset-incubator": {
            "description": "Incubation",
            "url": "https://github.com/dataciviclab/dataset-incubator",
        },
    },
    "datasets": {
        "Agenzia delle Entrate": [
            {
                "slug": "ade_cinque_per_mille",
                "name": "5x1000",
                "period": {"start": 2023, "end": 2025},
                "stage": "published",
            },
        ],
        "ANAC": [
            {
                "slug": "anac_bandi_gara",
                "name": "Bandi gara",
                "period": {"start": 2015, "end": 2024},
                "stage": "published",
            },
            {
                "slug": "anac_smartcig",
                "name": "SmartCIG",
                "period": {"start": 2020, "end": 2024},
                "stage": "incubating",
            },
        ],
    },
    "explorer_themes": [
        {
            "slug": "finanza-pubblica",
            "name": "Finanza pubblica",
            "datasets": ["ade_cinque_per_mille"],
        },
    ],
    "analyses": [
        {
            "slug": "cinque-per-mille",
            "name": "5x1000",
            "datasets": ["ade_cinque_per_mille"],
            "status": "active",
        },
    ],
    "analyses_by_dataset": {"ade_cinque_per_mille": ["cinque-per-mille"]},
    "operational_topics": {
        "pipeline": {
            "summary": "Ciclo di vita del dato",
            "repos": ["toolkit"],
            "next": "Flusso completo run + push GCS",
        },
    },
}

_MOCK_WORKSPACE_TRIAGE = {
    "generated_at": "2026-08-27T10:00:00",
    "repos": ["dataciviclab", "dataset-incubator"],
    "radar": {
        "available": True,
        "probe_date": "2026-08-26",
        "sources_total": 36,
        "green": 34,
        "yellow": 1,
        "red": 1,
        "persistent_red": 1,
        "sources": [
            {
                "id": "istat_sdmx",
                "status": "GREEN",
                "protocol": "sdmx",
                "http_code": "200",
                "note": "",
                "red_streak": 0,
            },
            {
                "id": "ispra_linked_data",
                "status": "RED",
                "protocol": "sparql",
                "http_code": "-",
                "note": "Connection error",
                "red_streak": 14,
            },
        ],
        "unhealthy": [
            {
                "id": "ispra_linked_data",
                "status": "RED",
                "protocol": "sparql",
                "note": "Connection error",
                "red_streak": 14,
            },
        ],
    },
    "source_health": {
        "available": True,
        "captured_at": "2026-08-26",
        "sources_checked": 36,
        "regressions": [],
        "alerts": [],
    },
    "pipeline_state": {
        "available": True,
        "generated_at": "2026-08-16",
        "summary": {"total": 100, "by_status": {"ok": 100}},
        "actionable": [],
    },
    "registry_summary": [
        {
            "repo": "dataset-incubator",
            "datasets": 92,
            "marts": 149,
            "signals": 100,
            "source_repo": "dataciviclab/dataset-incubator",
            "updated_at": "2026-08-16",
            "signals_detail": [
                {
                    "id": "aci_prime",
                    "source_id": "aci",
                    "status": "ok",
                    "label": "ACI",
                    "detail": "ok",
                },
                {
                    "id": "ispra_ru",
                    "source_id": "ispra",
                    "status": "ok",
                    "label": "ISPRA",
                    "detail": "ok",
                },
            ],
        },
        {
            "repo": "eurostat",
            "datasets": 30,
            "marts": 90,
            "signals": 30,
            "source_repo": "dataciviclab/eurostat",
            "updated_at": "2026-08-16",
            "signals_detail": [],
        },
    ],
    "discussions": [
        {"title": "Test discussion", "number": 1, "repo": "dataciviclab", "category": "Domande"},
    ],
    "prs": [],
    "issues": [],
    "git_state": {},
    "warnings": [],
}


# ── Helpers ─────────────────────────────────────────────────────────────────


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


# ── ACB-based loaders ──────────────────────────────────────────────────────


@pytest.mark.contract
class TestLoadCatalog:
    """Contratto: load_catalog() produce {datasets: [...]} da topic_index."""

    def test_flattens_datasets_from_topic_index(self):
        with patch("sources._fetch_json", return_value=_MOCK_TOPIC_INDEX):
            result = load_catalog()
        datasets = result["datasets"]
        assert len(datasets) == 3  # 1 ADE + 2 ANAC
        slugs = {ds["slug"] for ds in datasets}
        assert "ade_cinque_per_mille" in slugs
        assert "anac_bandi_gara" in slugs
        # 每个 dataset ha campo source
        for ds in datasets:
            assert "source" in ds

    def test_returns_empty_on_error(self):
        with patch("sources._fetch_json", side_effect=Exception("fail")):
            result = load_catalog()
        assert result == {"datasets": []}


@pytest.mark.contract
class TestLoadSignals:
    """Contratto: load_signals() produce {signals: [...]} da workspace_triage."""

    def test_builds_signals_from_registry_summary(self):
        with patch("sources._fetch_json", return_value=_MOCK_WORKSPACE_TRIAGE):
            result = load_signals()
        signals = result["signals"]
        assert len(signals) == 2  # 2 signals_detail from dataset-incubator
        ids = {s["id"] for s in signals}
        assert "aci_prime" in ids
        assert "ispra_ru" in ids

    def test_includes_pipeline_state(self):
        with patch("sources._fetch_json", return_value=_MOCK_WORKSPACE_TRIAGE):
            result = load_signals()
        assert "pipeline_state" in result
        assert result["pipeline_state"]["summary"]["total"] == 100


@pytest.mark.contract
class TestLoadRadar:
    """Contratto: load_radar() produce status_counts + sources da workspace_triage."""

    def test_transforms_radar_from_triage(self):
        with patch("sources._fetch_json", return_value=_MOCK_WORKSPACE_TRIAGE):
            result = load_radar()
        assert result["status_counts"] == {"GREEN": 34, "YELLOW": 1, "RED": 1}
        assert result["persistent_red"] == 1
        assert len(result["sources"]) == 2  # all sources (GREEN + RED)
        green = [s for s in result["sources"] if s["status"] == "GREEN"]
        red = [s for s in result["sources"] if s["status"] == "RED"]
        assert len(green) == 1
        assert len(red) == 1


@pytest.mark.contract
class TestLoadSourcesRegistry:
    """Contratto: load_sources_registry() legge da SO sources_registry.yaml."""

    def test_returns_per_source_registry(self):
        mock_data = {
            "istat_sdmx": {
                "protocol": "sdmx",
                "observation_mode": "api",
                "base_url": "https://...",
            },
            "ispra_ru": {
                "protocol": "sparql",
                "observation_mode": "endpoint",
                "base_url": "https://...",
            },
        }
        with patch("sources._fetch_yaml", return_value=mock_data):
            result = load_sources_registry()
        assert "istat_sdmx" in result
        assert result["istat_sdmx"]["protocol"] == "sdmx"

    def test_returns_empty_on_error(self):
        with patch("sources._fetch_yaml", side_effect=Exception("fail")):
            result = load_sources_registry()
        assert result == {}


@pytest.mark.contract
class TestLoadCatalogSignals:
    """Contratto: load_catalog_signals() legge da SO catalog_signals.json."""

    def test_returns_per_source_signals(self):
        mock_data = {
            "signals": [
                {
                    "source_id": "istat_sdmx",
                    "signal_type": "inventory",
                    "result": "stabile",
                    "metric_value": 100,
                },
            ]
        }
        with patch("sources._fetch_json", return_value=mock_data):
            result = load_catalog_signals()
        assert "signals" in result
        assert result["signals"][0]["source_id"] == "istat_sdmx"

    def test_returns_empty_on_error(self):
        with patch("sources._fetch_json", side_effect=Exception("fail")):
            result = load_catalog_signals()
        assert result == {}


@pytest.mark.contract
class TestLoadExplorerDatasets:
    """Contratto: load_explorer_datasets() estrae slug da explorer_themes."""

    def test_extracts_slugs(self):
        with patch("sources._fetch_json", return_value=_MOCK_TOPIC_INDEX):
            result = load_explorer_datasets()
        assert result == {"ade_cinque_per_mille"}

    def test_returns_empty_on_error(self):
        with patch("sources._fetch_json", side_effect=Exception("fail")):
            result = load_explorer_datasets()
        assert result == set()


@pytest.mark.contract
class TestLoadAnalyses:
    """Contratto: load_analyses() restituisce la lista analyses da topic_index."""

    def test_returns_analyses_list(self):
        with patch("sources._fetch_json", return_value=_MOCK_TOPIC_INDEX):
            result = load_analyses()
        assert len(result) == 1
        assert result[0]["slug"] == "cinque-per-mille"

    def test_returns_empty_on_error(self):
        with patch("sources._fetch_json", side_effect=Exception("fail")):
            assert load_analyses() == []


@pytest.mark.contract
class TestLoadOperationalTopics:
    """Contratto: load_operational_topics() restituisce il dict operational_topics."""

    def test_returns_topics(self):
        with patch("sources._fetch_json", return_value=_MOCK_TOPIC_INDEX):
            result = load_operational_topics()
        assert "pipeline" in result
        assert result["pipeline"]["repos"] == ["toolkit"]


@pytest.mark.contract
class TestLoadSourceHealth:
    """Contratto: load_source_health() restituisce regressions + alerts da triage."""

    def test_returns_health(self):
        with patch("sources._fetch_json", return_value=_MOCK_WORKSPACE_TRIAGE):
            result = load_source_health()
        assert result["available"] is True
        assert result["sources_checked"] == 36
        assert result["regressions"] == []


@pytest.mark.contract
class TestDeSlug:
    def test_known_mapping(self):
        assert de_slug("aifa_spesa_consumo") == "spesa-farmaceutica"

    def test_default_mapping(self):
        assert de_slug("ispra_ru_base") == "rifiuti-urbani"

    def test_generic_conversion(self):
        assert de_slug("some_dataset") == "some-dataset"

    def test_no_underscore(self):
        assert de_slug("nodash") == "nodash"
