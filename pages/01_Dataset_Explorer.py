"""Dataset Explorer — browse e filtra il catalogo. Mostra campi reali di clean_catalog.json."""
import streamlit as st
from sources import load_catalog, render_sidebar_common, data_freshness_note
render_sidebar_common()

st.title("Dataset Explorer")

catalog = load_catalog()
datasets = catalog.get("datasets", [])

stages = sorted(set(d.get("stage", "unknown") for d in datasets))
stage_filter = st.selectbox("Filtra per stage", ["Tutti"] + stages)

search = st.text_input("Cerca dataset", placeholder="slug, nome o descrizione...")

filtered = datasets
if stage_filter != "Tutti":
    filtered = [d for d in filtered if d.get("stage") == stage_filter]
if search:
    q = search.lower()
    filtered = [
        d for d in filtered
        if q in d.get("slug", "").lower()
        or q in d.get("name", "").lower()
        or q in d.get("description", "").lower()
    ]

st.write(f"**{len(filtered)} dataset** trovati")

for ds in filtered:
    period = ds.get("period", {})
    yrs = f"{period.get('start', '?')}–{period.get('end', '?')}" if period else "?"
    with st.expander(f"**{ds.get('slug', '?')}** — {ds.get('stage', '?')}"):
        st.write(f"**Nome:** {ds.get('name', '—')}")
        st.write(f"**Descrizione:** {ds.get('description', '—')}")
        st.write(f"**Fonte:** {ds.get('source', '?')}")
        st.write(f"**Anni:** {yrs}")
        loc = ds.get("location", {})
        if loc.get("path"):
            st.write(f"**Path GCS:** `{loc['path']}`")

data_freshness_note()
