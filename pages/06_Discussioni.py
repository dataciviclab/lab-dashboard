"""Discussioni — tutte le conversazioni pubbliche del Lab."""
import streamlit as st
from sources import (
    load_recent_discussions, load_discussion_counts,
    data_freshness_note, _github_token,
)

st.title("💬 Discussioni")

st.markdown(
    "Tutte le conversazioni pubbliche del Lab. "
    "Le discussioni sono il punto d'ingresso principale: "
    "chiunque può proporre un dataset, fare una domanda o pubblicare un'analisi."
)

# Controllo token
if not _github_token():
    st.warning(
        "⚠️ Per caricare le discussion serve un **GitHub Token**. "
        "Vai su ☰ → Settings → Secrets e aggiungi `github_token = \"ghp_...\"`."
    )

# Carica dati
disc_counts = load_discussion_counts()
all_discussions = load_recent_discussions(limit=30)

st.metric("💬 Discussioni totali", disc_counts.get("totale", "?"))

st.markdown("---")

# Filtri
if all_discussions:
    categories = sorted(set(d.get("category", {}).get("name", "?") for d in all_discussions))
    cat_filter = st.selectbox("Filtra per categoria", ["Tutte"] + categories)

    filtered = all_discussions
    if cat_filter != "Tutte":
        filtered = [d for d in filtered
                    if d.get("category", {}).get("name") == cat_filter]

    # Mostra discussioni raggruppate per categoria
    for cat in categories:
        cat_discs = [d for d in filtered
                     if d.get("category", {}).get("name") == cat]
        if not cat_discs:
            continue
        with st.expander(f"{cat} ({len(cat_discs)})", expanded=len(cat_discs) <= 5):
            for d in cat_discs:
                title = d.get("title", "")
                url = d.get("url", "")
                date = d.get("createdAt", "")[:10]
                st.write(f"- [{title}]({url}) · {date}")
else:
    st.info("Nessuna discussione caricata. Assicurati che il token GitHub sia configurato.")

data_freshness_note()

st.markdown("---")
st.caption(
    "Vuoi partecipare? "
    "[Apri una nuova discussione](https://github.com/dataciviclab/dataciviclab/discussions/new/choose)"
)
