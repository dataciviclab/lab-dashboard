# lab-dashboard

Dashboard operativi interni di DataCivicLab.

**Live**: [dataciviclab-dashboard.streamlit.app](https://dataciviclab-dashboard.streamlit.app/)

Basato su **Streamlit** + **DuckDB** + **Altair**. Legge metadati da GitHub raw e dati live da GCS parquet via DuckDB HTTP.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Apri http://localhost:8501

## Sezioni

| Pagina | Cosa mostra |
|---|---|
| **Vista d'insieme** | Metriche aggregate: count dataset, pipeline OK/warn/error, distribuzione per stage e tema |
| **Dataset Explorer** | Browse e filtra il catalogo completo per stage e parola chiave |
| **Pipeline Health** | Stato CI segnali da `pipeline_signals.json` con grafico a ciambella |
| **Copertura dati** | Matrice anni×dataset letta live dai parquet GCS via DuckDB |
| **Funnel Candidate** | Flusso SCOUTING → INTAKE → VALIDAZIONE → PUBBLICATI con tassi di conversione e rilevamento colli di bottiglia |
| **Radar Fonti** | Salute live dei 23 portali monitorati (GREEN/YELLOW/RED) con distribuzione per protocollo |

## Tema

Streamlit supporta tema chiaro e scuro nativamente:

☰ **Menu hamburger** (in alto a destra) → **Settings** → **Theme** → scegli **Dark** o **Light**

## Dati

| Fonte | URL | Cosa contiene |
|---|---|---|
| Metadati | `raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry/` | `clean_catalog.json`, `pipeline_signals.json` |
| Radar | `raw.githubusercontent.com/dataciviclab/source-observatory/main/data/radar/` | `radar_summary.json`, `sources_registry.yaml` |
| Dati live | `storage.googleapis.com/dataciviclab-clean/` | Parquet letti via DuckDB HTTP range requests |

## Deploy

Su **Streamlit Community Cloud**:
1. Collega il repo GitHub
2. App principale: `app.py`
3. Python version: 3.12
4. Deploy automatico a ogni push su `main`

## Stack

- **Streamlit** — framework app
- **DuckDB** — query engine per parquet su GCS
- **Altair** — chart declarativi
- **Requests** — fetch metadati da GitHub raw
- **PyYAML** — parsing sources_registry.yaml
