# lab-dashboard

Dashboard operativi interni di DataCivicLab.

**Live**: [dataciviclab-dashboard.streamlit.app](https://dataciviclab-dashboard.streamlit.app/)

Basato su **Streamlit** + **DuckDB** + **Altair**. Legge metadati da GitHub raw e dati live da GCS parquet.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sezioni

| Pagina | Cosa mostra |
|---|---|
| **Vista d'insieme** | Metriche aggregate: dataset, pipeline OK/warn/error, stage, temi |
| **Dataset Explorer** | Browse e filtra i 24+ dataset del catalogo |
| **Pipeline Health** | Stato segnali CI da pipeline_signals.json |
| **Copertura dati** | Matrice anni×dataset letta live dai parquet GCS via DuckDB |
| **Funnel Candidate** | Flusso SCOUTING → INTAKE → VALIDAZIONE → PUBBLICATI con tassi di conversione |
| **Radar Fonti** | Salute dei portali monitorati (GREEN/YELLOW/RED) |

## Dati

| Fonte | URL | Cosa |
|---|---|---|
| Metadati | `raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry/` | `clean_catalog.json`, `pipeline_signals.json` |
| Radar | `raw.githubusercontent.com/dataciviclab/source-observatory/main/data/radar/` | `radar_summary.json`, `sources_registry.yaml` |
| Dati live | `storage.googleapis.com/dataciviclab-clean/` | Parquet letti via DuckDB HTTP range requests |

## Deploy

Su **Streamlit Community Cloud**:
1. Connetti il repo GitHub
2. App principale: `app.py`
3. Python version: 3.12
4. Deploy automatico a ogni push su `main`
