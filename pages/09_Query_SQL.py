"""Query SQL interattiva sui dataset pubblici del DataCivicLab."""

from lab_connectors.duckdb.sql_page import render_sql_query
from lab_connectors.registry import Column, Dataset, Location, Registry

from sources import data_freshness_note, load_catalog


def _build_registry_from_acb() -> Registry:
    """Build a Registry object from ACB topic_index data.

    Only includes datasets with a valid GCS location (path non-empty).
    """
    catalog = load_catalog()
    datasets = []
    for ds in catalog.get("datasets", []):
        loc_data = ds.get("location", {})
        path = loc_data.get("path", "")
        if not path:
            continue  # Skip datasets without GCS location
        is_multi = loc_data.get("multi_file", True)
        location = Location(type=loc_data.get("type", "gcs"), path=path, multi_file=is_multi)
        columns = [
            Column(
                name=c.get("name", ""),
                type=c.get("type", ""),
                role=c.get("role", ""),
                description=c.get("description", ""),
            )
            for c in ds.get("columns", [])
        ]
        datasets.append(
            Dataset(
                slug=ds.get("slug", ""),
                name=ds.get("name", ""),
                description=ds.get("description", ""),
                source=ds.get("source", ""),
                source_id=ds.get("source_id", ""),
                period=ds.get("period", {}),
                stage=ds.get("stage", ""),
                columns=columns,
                location=location,
            )
        )
    return Registry(schema_version=1, repo="acb", datasets=datasets)


registry = _build_registry_from_acb()
render_sql_query(
    registry=registry,
    title="🧪 Query SQL",
    description=(
        "Scrivi query **SQL** sui dataset pubblici. "
        "Usa ``clean_input`` come nome della tabella virtuale — "
        "viene risolta automaticamente sui **Parquet GCS**."
    ),
)
data_freshness_note()
