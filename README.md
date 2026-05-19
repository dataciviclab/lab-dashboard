# lab-dashboard

Dashboard operativi interni di DataCivicLab.

**Live**: [dataciviclab-dashboard.streamlit.app](https://dataciviclab-dashboard.streamlit.app/)

Basato su **Streamlit** + **DuckDB** + **Altair**. Legge metadati da GitHub raw, report da GCS e discussioni via GitHub GraphQL API.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Apri http://localhost:8501

## Navigazione

| Sezione | Pagina | Cosa mostra |
|---|---|---|
| — | **Vista d'insieme** | Metriche globali: dataset, fonti attive, pipeline OK, discussioni recenti |
| **Source Observatory** | **Stato e KPI** | Funnel SO (23→23→15→5→6), radar trend storico, tabella fonti unificata con inventario e segnali |
| **Dataset Incubator** | **Pipeline CI** | Segnali CI, success rate run (passed/failed), candidate distribuite per fonte |
| | **Funnel candidate** | Flusso SCOUTING → INTAKE → VALIDAZIONE → PUBBLICATI, tag compose |
| | **Copertura dati** | Matrice anni×dataset letta live dai parquet GCS via DuckDB |
| **Catalogo** | **Esplora dataset** | Browse catalogo con schema colonne (nome, tipo, ruolo) |
| **Community** | **Discussioni** | GitHub Discussions del Lab via GraphQL API |

## Dati

| Fonte | Artifact | Consumato da |
|---|---|---|
| **dataset-incubator** `registry/` | `clean_catalog.json`, `pipeline_signals.json` | Vista d'insieme, Pipeline CI, Funnel, Copertura, Explorer |
| **source-observatory** `data/radar/` | `radar_summary.json`, `radar_history.json`, `sources_registry.yaml` | Source Observatory, Funnel |
| **source-observatory** `data/catalog/` | `catalog_signals.json` | Source Observatory |
| **source-observatory** GCS | `catalog_inventory_report.json` | Source Observatory (badge inventario) |
| **GitHub GraphQL** | Discussions API | Vista d'insieme, Discussioni |

## Deploy

Su **Streamlit Community Cloud**:

1. Collega il repo GitHub
2. App principale: `app.py`
3. Python version: 3.12
4. Deploy automatico a ogni push su `main`

## CI

Su ogni push/PR: `ruff` lint + `pytest` (17 test su `sources.py`).

## Stack

- **Streamlit** — framework app, navigazione gerarchica (`st.navigation`)
- **DuckDB** — query engine per parquet su GCS
- **Altair** — chart dichiarativi (line chart, heatmap, ciambella, barre)
- **Requests** — fetch metadati da GitHub raw e GCS
- **PyYAML** — parsing `sources_registry.yaml`
