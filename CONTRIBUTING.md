# Contributing to lab-dashboard

Questa guida vale per la repo `lab-dashboard`.

Per le regole GitHub condivise dell'organizzazione, parti prima da
[`.github`](https://github.com/dataciviclab/.github).

## A cosa serve questa repo

`lab-dashboard` è la dashboard operativa interna di DataCivicLab.
Mostra metriche e stato in tempo reale su fonti, pipeline, dataset e discussioni.

**Live**: [dataciviclab-dashboard.streamlit.app](https://dataciviclab-dashboard.streamlit.app/)

Basata su **Streamlit** + **DuckDB** + **Altair**.

Qui stanno:

- `app.py` — entry point della dashboard
- `pages/` — pagine Streamlit per sezione (Source Observatory, Dataset Incubator, Catalogo, Community)
- `sources.py` — logica di fetch e parsing delle fonti dati upstream
- `tests/` — test su `sources.py` e pagine
- `static/` — asset statici

Qui non stanno:

- pipeline di trasformazione dati — va in `dataset-incubator` + `toolkit`
- scouting e monitoraggio fonti — va in `source-observatory`
- il sito pubblico del Lab — va in `dataciviclab` (Astro)
- package condivisi di infrastruttura — vanno in `lab-connectors`
- policy GitHub comuni — vanno in `.github`

## Setup locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

Apri http://localhost:8501

### Eseguire i test

```bash
pytest tests/
ruff check .
```

## Dati consumati

La dashboard legge dati da artifact upstream in sola lettura:

| Fonte | Artifact | Uso |
|---|---|---|
| `dataset-incubator` | `registry/clean_catalog.json`, `pipeline_signals.json` | Metriche dataset, pipeline CI |
| `source-observatory` | `data/radar/radar_summary.json`, `radar_history.json` | Stato fonti, radar trend |
| `source-observatory` | `data/catalog/catalog_signals.json` | Inventory fonti |
| GitHub GraphQL API | Discussions | Community metrics |

## Deploy

La dashboard è deployata su **Streamlit Community Cloud**:

1. Collegata al repo GitHub
2. App principale: `app.py`
3. Python version: 3.12
4. Deploy automatico a ogni push su `main`

La CI esegue `ruff` lint + `pytest` su ogni push e PR.

## Quando aprire una issue

Apri una issue in `lab-dashboard` se il lavoro riguarda:

- nuova metrica o visualizzazione
- cambio struttura dati consumata da upstream
- bug o miglioramenti dell'interfaccia
- performance o caching

Per discutere una nuova sezione della dashboard prima di aprirla,
usa una Discussion in `dataciviclab`.

## Prima di aprire una PR

- verifica se esiste già una issue collegata
- tieni il perimetro stretto: una PR = una sezione o un fix
- se modifichi `sources.py`, controlla che i test passino
- se aggiungi una pagina, segui la struttura delle pagine esistenti in `pages/`
- se cambi il formato di un dato upstream, coordina con `source-observatory`
  o `dataset-incubator`
- verifica localmente con `streamlit run app.py` che tutto funzioni

## Riferimenti

- [README.md](README.md) — panoramica della dashboard
- [`.github`](https://github.com/dataciviclab/.github) — policy condivise
- [`source-observatory`](https://github.com/dataciviclab/source-observatory) — upstream radar/inventory
- [`dataset-incubator`](https://github.com/dataciviclab/dataset-incubator) — upstream catalogo/pipeline
