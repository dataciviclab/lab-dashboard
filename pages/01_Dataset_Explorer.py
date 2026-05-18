"""Dataset Explorer — browse e filtra il catalogo."""
import streamlit as st
from sources import load_catalog

st.title("Dataset Explorer")

catalog = load_catalog()
datasets = catalog.get("datasets", [])

stages = sorted(set(d.get("stage", "unknown") for d in datasets))
stage_filter = st.selectbox("Filtra per stage", ["Tutti"] + stages)

search = st.text_input("Cerca dataset", placeholder="slug o descrizione...")

filtered = datasets
if stage_filter != "Tutti":
    filtered = [d for d in filtered if d.get("stage") == stage_filter]
if search:
    filtered = [
        d
        for d in filtered
        if search.lower() in d.get("slug", "").lower()
        or search.lower() in d.get("description", "").lower()
    ]

st.write(f"**{len(filtered)} dataset** trovati")

for ds in filtered:
    with st.expander(f"**{ds.get('slug', '?')}** — {ds.get('stage', '?')}"):
        st.write(f"**Descrizione:** {ds.get('description', '—')}")
        st.write(f"**Fonte:** {ds.get('source', '?')}")
        st.write(f"**Anni:** {ds.get('year_range', '?')}")
        if ds.get("url"):
            st.write(f"**URL:** {ds['url']}")
        if ds.get("discussion_url"):
            st.write(f"**Discussione:** {ds['discussion_url']}")
