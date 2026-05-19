"""
Dettaglio candidate — candidati, incubazione e dataset pubblicati.
Il funnel è nella Vista d'insieme; qui solo il dettaglio operativo.
"""
import streamlit as st
from sources import load_catalog, load_signals, data_freshness_note
st.title("📥 Dettaglio candidate")

st.markdown(
    "Elenco dei candidati in pipeline, "
    "dal intake (dataset.yml + CI) alla pubblicazione in Explorer."
)

# ── Carica dati ───────────────────────────────────────────────────────────────
catalog = load_catalog()
signals = load_signals()

datasets = catalog.get("datasets", [])
sigs = signals.get("signals", [])

# ── Classifica ────────────────────────────────────────────────────────────────
catalog_slugs = set(ds["slug"] for ds in datasets)
candidati = []
for sig in sigs:
    slug = sig["id"].replace("-", "_")
    if slug not in catalog_slugs:
        sr = sig.get("sample_run", {}) or {}
        candidati.append({
            "slug": slug,
            "id": sig["id"],
            "label": sig.get("label", slug),
            "source_id": sig.get("source_id", "?"),
            "status": sig.get("status", "?"),
            "detail": sig.get("detail", ""),
            "checked_at": sr.get("checked_at", "?"),
            "run_url": sr.get("run_url", ""),
            "run_status": sr.get("status", ""),
            "tipo": "compose" if sig["id"].startswith("compose:") else "candidate",
        })

incubazione = []
published_datasets = []
for ds in datasets:
    stage = ds.get("stage", "")
    item = {
        "slug": ds["slug"],
        "name": ds.get("name", ""),
        "source_id": ds.get("source_id", "?"),
        "description": ds.get("description", "")[:120],
    }
    if stage == "published":
        published_datasets.append(item)
    elif stage == "incubating":
        incubazione.append(item)

n_failed = sum(1 for c in candidati if c["run_status"] == "failed")
n_intake = len(candidati)
n_validation = len(incubazione)
n_published = len(published_datasets)

# ══════════════════════════════════════════════════════════════════
# TAB PER AZIONE
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    f"📋 Da rivedere ({n_failed})",
    f"🔬 In corso ({n_intake + n_validation - n_failed})",
    f"✅ Completati ({n_published})",
])

with tab1:
    """Candidate con run CI fallito."""
    failed = [c for c in candidati if c["run_status"] == "failed"]
    if failed:
        for c in failed:
            run_badge = "❌ fallito"
            tag = "🧩 compose" if c["tipo"] == "compose" else ""
            title = f"❌ **{c['label']}** — {c['source_id']}"
            if tag:
                title += f" · {tag}"
            with st.expander(title):
                st.write(f"**Dettaglio:** {c['detail']}")
                st.write(f"**Ultimo check:** {c['checked_at']}")
                st.write(f"**Ultimo run:** {run_badge}")
                if c["run_url"]:
                    st.write(f"**Run CI:** [{c['run_url']}]({c['run_url']})")
    else:
        st.success("Nessun candidate con run fallito.")

with tab2:
    """Candidate in corso e dataset in incubazione."""
    st.markdown(f"**📥 Candidate intake ({n_intake - n_failed})**")
    st.caption("dataset.yml + pipeline CI, in attesa di clean parquet su GCS")
    for c in candidati:
        if c["run_status"] == "failed":
            continue
        run_badge = {"passed": "✅ passato", "": "⚪ in attesa"}.get(
            c["run_status"], "⚪ sconosciuto"
        )
        e = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(c["status"], "❓")
        tag = "🧩 compose" if c["tipo"] == "compose" else ""
        title = f"{e} **{c['label']}** — run: {run_badge}"
        if tag:
            title += f" · {tag}"
        with st.expander(title):
            st.write(f"**Dettaglio:** {c['detail']}")
            st.write(f"**Fonte:** {c['source_id']}")
            st.write(f"**Ultimo check:** {c['checked_at']}")
            if c["run_url"]:
                st.write(f"**Run CI:** [{c['run_url']}]({c['run_url']})")

    st.markdown("---")
    st.markdown(f"**🔬 In incubazione ({n_validation})**")
    st.caption("Clean parquet su GCS, in attesa di pubblicazione in Explorer")
    for ds in incubazione:
        with st.expander(f"🔬 **{ds['slug']}** — fonte: {ds['source_id']}"):
            st.write(f"**Nome:** {ds['name']}")
            st.write(f"**Descrizione:** {ds['description']}")

with tab3:
    """Dataset pubblicati nell'Explorer."""
    for ds in published_datasets:
        with st.expander(f"✅ **{ds['slug']}** — fonte: {ds.get('source_id', '?')}"):
            st.write(f"**Nome:** {ds.get('name', '?')}")
            st.write(f"**Descrizione:** {ds.get('description', '?')}")

data_freshness_note()

st.caption(
    "Dati: dataset-incubator (pipeline_signals + clean_catalog) · "
    "Il funnel complessivo è nella **Vista d'insieme**."
)
