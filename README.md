# lab-dashboard

Dashboard operativi interni di DataCivicLab.

**Live**: [dataciviclab-dashboard.streamlit.app](https://dataciviclab-dashboard.streamlit.app/)

## Architettura dati

La dashboard consuma da **2 fonti**:

| Fonte | Artifact | Cosa fornisce |
|---|---|---|
| **agent-context-builder** | `topic_index.json` + `workspace_triage.json` | Catalogo dataset, analisi, radar, segnali pipeline, alert, PR, issues, discussions |
| **source-observatory** | `radar_history.json`, `sources_registry.yaml`, `sources_dashboard.json`, `catalog_signals.json`, `source_reports/` | Radar storico, inventario per fonte, source reports |
| **GCS** (DuckDB) | Parquet clean/mart | Query SQL, verifica parquet |

## Setup

```bash
pip install -e ".[dev]"
streamlit run app.py
```

## Pagine

| Pagina | Fonte | Cosa mostra |
|---|---|---|
| **Vista d'insieme** | ACB | KPI radar, dataset, pipeline, PR/issues/discussions, alert Lab |
| **Catalogo** | ACB | Filtri per fonte/stage/categoria, tabella compatta, copertura anni, verifica parquet |
| **Analisi** | ACB | Analisi pubblicate collegate ai dataset (con link Explorer) |
| **Registry / Repo** | ACB | Stato registry per repo + temi operativi (pipeline/governance/infrastructure) |
| **Radar** | ACB + SO | 36 fonti, trend storico, attenzioni operative |
| **Inventario** | SO | Items cataloghi, source check, verdict per fonte |
| **Scheda fonte** | SO | Deep-dive: health, inventory, source check, dataset in uso |
| **Query SQL** | ACB + GCS | Query interattiva su parquet GCS (via lab-connectors) |
| **PR · Issues · Discussions** | ACB | Community aperta: PR, issues, discussions con ricerca e link GitHub |

## Stack

- **Streamlit** — framework app (`st.navigation`)
- **DuckDB** — query engine per parquet su GCS
- **Altair** — chart dichiarativi
- **lab-connectors** — path contract GCS, SQL page riutilizzabile

## Deploy

Streamlit Community Cloud: push su `main` → deploy automatico.
`requirements.txt` è un pin export per il deploy — source of truth: `pyproject.toml`.

## CI

`ruff` lint + `pytest` (marker contract/policy/smoke). Smoke test su rete reale solo su `main`.
