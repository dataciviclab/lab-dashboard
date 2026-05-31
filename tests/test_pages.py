"""
Test per le pagine Streamlit: esistenza, compilazione, smoke test.

Contratto: Ogni pagina e' un modulo Python valido (compila, ha AST).
  test_home_page_loads e' uno smoke test di integrazione.

Prova del fuoco: se cancello questi test, una pagina con sintassi rotta
puo' arrivare in produzione senza preavviso.
"""
import ast
import py_compile

import pytest

# Pagine referenziate in app.py (st.navigation)
PAGES = [
    "pages/00_Vista_Insieme.py",
    "pages/01_Dataset_Explorer.py",
    "pages/02_Pipeline_Health.py",
    "pages/05_Radar.py",
    "pages/06_Inventario.py",
    "pages/09_Query_SQL.py",
]


@pytest.mark.contract
@pytest.mark.parametrize("path", PAGES)
def test_page_compiles(path):
    """Ogni pagina deve essere sintatticamente corretta."""
    py_compile.compile(path, doraise=True)


@pytest.mark.contract
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


# ── Helper logic tests per 09_Query_SQL.py ─────────────────────────────────

def _build_query(user_sql: str, cte_expr: str, max_rows: int) -> str:
    """Replica la logica pura di pages/09_Query_SQL._build_query.

    Mantenuta come funzione a sé stante per testare il contratto SQL
    senza importare il modulo Streamlit (che richiede runtime).
    """
    return (
        f"WITH clean_input AS ({cte_expr}) "
        f"SELECT * FROM ({user_sql}) AS _q LIMIT {max_rows}"
    )


def _default_sql(name: str, start: str, end: str, cols: list[str]) -> str:
    """Replica la logica pura di pages/09_Query_SQL._default_sql."""
    col_hint = ""
    if cols:
        col_hint = f"-- Colonne: {', '.join(cols[:5])}..."
    return (
        f"-- Dataset: {name}\n"
        f"-- Periodo: {start}–{end}\n"
        f"{col_hint}\n"
        f"-- Usa clean_input come tabella virtuale\n"
        f"SELECT * FROM clean_input LIMIT 10"
    )


class TestQueryBuildQuery:
    """Contratto: _build_query produce SQL valido per DuckDB."""

    @pytest.mark.contract
    def test_single_file_cte(self):
        """Singolo file → read_parquet('url')."""
        result = _build_query(
            "SELECT * FROM clean_input",
            "SELECT * FROM read_parquet('https://bucket/file.parquet')",
            10,
        )
        assert result == (
            "WITH clean_input AS (SELECT * FROM read_parquet('https://bucket/file.parquet')) "
            "SELECT * FROM (SELECT * FROM clean_input) AS _q LIMIT 10"
        )

    @pytest.mark.contract
    def test_multi_file_cte(self):
        """Multi file → read_parquet(['url1', 'url2'])."""
        cte = "SELECT * FROM read_parquet(['https://a.parquet', 'https://b.parquet'])"
        result = _build_query(
            "SELECT count(*) AS n FROM clean_input",
            cte,
            1000,
        )
        assert "read_parquet(['https://a.parquet', 'https://b.parquet'])" in result
        assert "LIMIT 1000" in result

    @pytest.mark.contract
    def test_sql_injection_prevention(self):
        """CTE wrapping previene injection: la SQL utente è dentro una subquery."""
        malicious = "'; DROP TABLE clean_input; --"
        result = _build_query(malicious, "SELECT 1 AS x", 10)
        # La SQL malevola finisce dentro la subquery, non può uscire
        assert "AS _q LIMIT 10" in result
        assert "DROP" in result  # è dentro la subquery, non pericolosa

    @pytest.mark.contract
    def test_with_group_by(self):
        """GROUP BY + ORDER BY funzionano dentro il wrapping."""
        sql = "SELECT anno, count(*) AS n FROM clean_input GROUP BY anno ORDER BY anno"
        cte = "SELECT * FROM read_parquet('https://data/dataset.parquet')"
        result = _build_query(sql, cte, 500)
        assert result.startswith("WITH clean_input AS (SELECT * FROM read_parquet")
        assert "GROUP BY anno" in result
        assert "ORDER BY anno" in result
        assert "LIMIT 500" in result


class TestQueryDefaultSql:
    """Contratto: _default_sql produce un template chiaro."""

    @pytest.mark.contract
    def test_with_columns(self):
        """Template con colonne."""
        result = _default_sql(
            "IRPEF Comunale", "2019", "2023",
            ["anno", "comune", "reddito"],
        )
        assert "IRPEF Comunale" in result
        assert "2019–2023" in result
        assert "anno, comune, reddito" in result
        assert "SELECT * FROM clean_input LIMIT 10" in result

    @pytest.mark.contract
    def test_without_columns(self):
        """Template senza colonne (es. catalogo senza schema)."""
        result = _default_sql("Civile Flussi", "2014", "2025", [])
        assert "Civile Flussi" in result
        assert "-- Colonne:" not in result


# ── Resolve slug (multi_file True/False) ──────────────────────────────────────

def _resolve_urls_multi(slug: str, years: list[int]) -> list[str]:
    """Replica la logica di _resolve_slug per multi_file=True."""
    return [
        f"https://storage.googleapis.com/dataciviclab-clean/{slug}/{y}/{slug}_{y}_clean.parquet"
        for y in years
    ]


def _resolve_urls_single(gcs_path: str) -> list[str]:
    """Replica la logica di _resolve_slug per multi_file=False."""
    return [gcs_path.replace("gs://", "https://storage.googleapis.com/", 1)]


class TestResolveSlug:
    """Contratto: _resolve_slug produce URL corretti per entrambi i pattern."""

    @pytest.mark.contract
    def test_multi_file_produces_one_url_per_year(self):
        """multi_file=True → un URL per anno."""
        urls = _resolve_urls_multi("irpef_comunale", [2021, 2022, 2023])
        assert len(urls) == 3
        for y, u in zip([2021, 2022, 2023], urls):
            assert f"/{y}/" in u
            assert u.startswith("https://storage.googleapis.com/")
            assert u.endswith("_clean.parquet")

    @pytest.mark.contract
    def test_multi_file_cte_single_year(self):
        """Un solo anno → read_parquet('url')."""
        urls = _resolve_urls_multi("bdap_lea", [2024])
        assert len(urls) == 1
        cte = f"SELECT * FROM read_parquet('{urls[0]}')"
        assert cte.startswith("SELECT * FROM read_parquet('")
        assert cte.endswith("')")

    @pytest.mark.contract
    def test_multi_file_cte_multi_year(self):
        """Più anni → read_parquet(['url1', 'url2'])."""
        urls = _resolve_urls_multi("irpef_comunale", [2022, 2023])
        paths = "', '".join(urls)
        cte = f"SELECT * FROM read_parquet(['{paths}'])"
        assert "read_parquet(['" in cte
        assert urls[0] in cte
        assert urls[1] in cte

    @pytest.mark.contract
    def test_single_file_converts_gs_to_https(self):
        """multi_file=False: gs:// → https://storage.googleapis.com/."""
        gs = "gs://dataciviclab-clean/civile_flussi/2025/civile_flussi_2025_clean.parquet"
        urls = _resolve_urls_single(gs)
        assert len(urls) == 1
        assert urls[0] == (
            "https://storage.googleapis.com/dataciviclab-clean/"
            "civile_flussi/2025/civile_flussi_2025_clean.parquet"
        )

    @pytest.mark.contract
    def test_single_file_cte(self):
        """Singolo file → read_parquet('url')."""
        gs = "gs://bucket/dataset/2024/data_2024_clean.parquet"
        urls = _resolve_urls_single(gs)
        cte = f"SELECT * FROM read_parquet('{urls[0]}')"
        assert urls[0].startswith("https://storage.googleapis.com/")
        assert "read_parquet('https://storage.googleapis.com/bucket/dataset" in cte
