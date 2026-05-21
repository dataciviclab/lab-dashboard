"""
Fixture e setup condivisi per i test di lab-dashboard.

Neutralizza st.cache_data e st.error prima che sources.py venga importato,
cosi' i decoratori @st.cache_data non interferiscono con i test.
"""
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Neutralizza streamlit PRIMA che qualsiasi test file importi sources.py
# (st.cache_data viene usato come decoratore a tempo di importazione)
import streamlit as st

st.cache_data = lambda **kwargs: lambda f: f  # type: ignore[method-assign]
st.error = lambda msg: None  # type: ignore[method-assign]


@pytest.fixture
def mock_http_get() -> Callable:
    """Fixture che patch sources._HTTP.get e restituisce un MagicMock.

    Usa: con mock_http_get() as mock_get:
             mock_get.return_value = _resp({"key": "value"})
    """
    with patch("sources._HTTP.get") as mock:
        yield mock


@pytest.fixture
def mock_requests_post() -> Callable:
    """Fixture che patch sources.requests.post per test GraphQL."""
    with patch("sources.requests.post") as mock:
        yield mock


@pytest.fixture
def mock_duckdb_connect() -> Callable:
    """Fixture che patch sources.duckdb.connect per test DuckDB."""
    with patch("sources.duckdb.connect") as mock:
        yield mock


def _resp(data: Any, status: int = 200) -> MagicMock:
    """Crea una mock response requests con dati JSON."""
    import json
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.text = json.dumps(data)
    if status >= 400:
        m.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        m.raise_for_status.return_value = None
    return m


def _yaml_resp(text: str, status: int = 200) -> MagicMock:
    """Crea una mock response requests con testo YAML."""
    m = MagicMock()
    m.status_code = status
    m.text = text
    if status >= 400:
        m.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        m.raise_for_status.return_value = None
    return m
