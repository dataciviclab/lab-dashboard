# lab-dashboard

Dashboard operativi interni di DataCivicLab.

Basato su **Streamlit** + **DuckDB** + **Altair**.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Dati

| Fonte | URL | Cosa |
|---|---|---|
| Metadati | `raw.githubusercontent.com/dataciviclab/dataset-incubator/main/registry/` | `clean_catalog.json`, `pipeline_signals.json` |
| Dati live | `storage.googleapis.com/dataciviclab-clean/` | Tutti i parquet puliti, letti via DuckDB HTTP |

## Deploy

Su **Streamlit Community Cloud**:
1. Connetti il repo GitHub
2. App principale: `app.py`
3. Python version: 3.12
4. Deploy automatico a ogni push su `main`

## Sezioni

- **Vista d'insieme** — metriche aggregate, dataset per stage e tema
- **Dataset Explorer** — browse e filtra i 24+ dataset del catalogo
- **Pipeline Health** — stato segnali da `pipeline_signals.json`
- **Copertura dati** — matrice anni×dataset letta live dai parquet GCS
