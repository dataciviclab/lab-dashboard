"""Community — PR, issues e discussions aperte del Lab."""

import pandas as pd
import streamlit as st

from sources import data_freshness_note, load_workspace_triage

st.title("💬 Community")
st.markdown("PR, issues e discussions aperte — da `workspace_triage.json` (ACB).")

triage = load_workspace_triage()
prs = triage.get("prs", []) or []
issues = triage.get("issues", []) or []
discussions = triage.get("discussions", []) or []

if not (prs or issues or discussions):
    st.error("Dati community non disponibili.")
    st.stop()

# ── KPI ─────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("🔀 PR aperte", len(prs))
col2.metric("📌 Issues aperte", len(issues))
col3.metric("💬 Discussions", len(discussions))

st.markdown("---")

search = st.text_input("Cerca", placeholder="titolo, repo, numero...", key="comm_search")


def _filter(items: list[dict]) -> list[dict]:
    if not search:
        return items
    q = search.lower()
    return [
        i
        for i in items
        if q in i.get("title", "").lower()
        or q in i.get("repo", "").lower()
        or q in str(i.get("number", ""))
    ]


def _render_items(items: list[dict]) -> None:
    filtered = _filter(items)
    if not filtered:
        st.info("Nessun risultato.")
        return
    df = pd.DataFrame(
        [
            {
                "repo": i.get("repo", ""),
                "#": i.get("number", ""),
                "titolo": i.get("title", ""),
                "categoria": i.get("category", ""),
                "url": i.get("url", ""),
            }
            for i in filtered
        ]
    )
    st.dataframe(
        df,
        column_config={
            "repo": st.column_config.TextColumn("Repo", width="medium"),
            "#": st.column_config.NumberColumn("#", format="%d"),
            "titolo": st.column_config.TextColumn("Titolo", width="large"),
            "categoria": st.column_config.TextColumn("Categoria", width="small"),
            "url": st.column_config.LinkColumn("Link", display_text="apri"),
        },
        hide_index=True,
        width="stretch",
        height=min(35 * len(df) + 35, 500),
    )
    st.caption(f"{len(filtered)} risultati")


# ── Tab ─────────────────────────────────────────────────────────
tab_pr, tab_issues, tab_disc = st.tabs(
    [f"🔀 PR ({len(prs)})", f"📌 Issues ({len(issues)})", f"💬 Discussions ({len(discussions)})"]
)
with tab_pr:
    _render_items(prs)
with tab_issues:
    _render_items(issues)
with tab_disc:
    _render_items(discussions)

data_freshness_note()
