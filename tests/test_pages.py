"""
Test per le pagine Streamlit: esistenza, compilazione, smoke test.
"""
import py_compile
import ast

import pytest

# Pagine referenziate in app.py (st.navigation)
PAGES = [
    "pages/00_Vista_Insieme.py",
    "pages/01_Dataset_Explorer.py",
    "pages/02_Pipeline_Health.py",
    "pages/03_Copertura_Dati.py",
    "pages/04_Funnel_Candidate.py",
    "pages/05_Source_Observatory.py",
    "pages/06_Discussioni.py",
]


@pytest.mark.parametrize("path", PAGES)
def test_page_compiles(path):
    """Ogni pagina deve essere sintatticamente corretta."""
    py_compile.compile(path, doraise=True)


@pytest.mark.parametrize("path", PAGES)
def test_page_is_valid_python(path):
    """Ogni pagina deve essere un modulo Python valido (AST parse)."""
    with open(path) as fh:
        ast.parse(fh.read())


@pytest.mark.smoke
def test_home_page_loads():
    """Smoke test: Vista d'insieme si carica senza eccezioni.

    Usa AppTest di Streamlit per avviare la pagina in un ambiente simulato.
    Esegue richieste HTTP reali (GitHub raw, GCS) — se la rete è lenta
    o inaccessibile, il test fallisce con timeout.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("pages/00_Vista_Insieme.py")
    at.run(timeout=30)
    assert not at.exception, f"Pagina solleva eccezione: {at.exception}"
    assert len(at.metric) > 0, "La pagina deve avere almeno una metrica"
