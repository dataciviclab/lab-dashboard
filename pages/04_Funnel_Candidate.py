"""
Funnel candidate — pipeline dei dataset: da candidate a pubblicati.
Visione d'insieme del flusso intake → incubazione → pubblicazione.
"""
import streamlit as st
from sources import load_catalog, load_signals, data_freshness_note
st.title("📥 Funnel candidate")

st.markdown(
    "Pipeline dei dataset del Lab: "
    "dal candidate (dataset.yml + CI) alla pubblicazione in Explorer. "
    "Il funnel mostra la progressione; i tab sotto il dettaglio operativo."
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

n_intake = len(candidati)
n_validation = len(incubazione)
n_published = len(published_datasets)
n_failed = sum(1 for c in candidati if c["run_status"] == "failed")
n_compose = sum(1 for c in candidati if c["tipo"] == "compose")

# ══════════════════════════════════════════════════════════════════
# FUNNEL
# ══════════════════════════════════════════════════════════════════
st.subheader("Pipeline")

max_n = max(n_intake, n_validation, n_published, 1)
stages = [
    ("📥 Intake", n_intake, "#3b82f6", f"{n_compose} compose"),
    ("🔬 Incubazione", n_validation, "#f59e0b", ""),
    ("✅ Pubblicati", n_published, "#16a34a", ""),
]

for label, count, color, note in stages:
    pct = count / max_n if max_n else 0
    cols = st.columns([2.5, 12])
    with cols[0]:
        st.write(f"**{label}**")
    with cols[1]:
        note_html = f"<span style='font-size:0.85em;color:gray;'> · {note}</span>" if note else ""
        bar_html = f"""
        <div style="border-radius:8px; height:32px; overflow:hidden;">
            <div style="background:{color}; width:{pct*100:.0f}%; height:100%;
                border-radius:8px; display:flex; align-items:center; padding-left:10px;">
                <span style="font-weight:bold; font-size:16px;">{count}{note_html}</span>
            </div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)

# Alert
if n_failed:
    st.error(f"❌ **{n_failed} candidate con run fallito** — vedi tab Da rivedere")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# TAB PER AZIONE
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    f"📋 Da rivedere ({n_failed})",
    f"🔬 In corso ({n_intake + n_validation - n_failed})",
    f"✅ Completati ({n_published})",
])

with tab1:
    failed = [c for c in candidati if c["run_status"] == "failed"]
    if failed:
        for c in failed:
            tag = "🧩 compose" if c["tipo"] == "compose" else ""
            title = f"❌ **{c['label']}** — {c['source_id']}"
            if tag:
                title += f" · {tag}"
            with st.expander(title):
                st.write(f"**Dettaglio:** {c['detail']}")
                st.write(f"**Ultimo check:** {c['checked_at']}")
                st.write("**Ultimo run:** ❌ fallito")
                if c["run_url"]:
                    st.write(f"**Run CI:** [{c['run_url']}]({c['run_url']})")
    else:
        st.success("Nessun candidate con run fallito.")

with tab2:
    st.markdown(f"**📥 Candidate intake ({n_intake - n_failed})**")
    st.caption("dataset.yml + pipeline CI, in attesa di clean parquet su GCS")
    for c in candidati:
        if c["run_status"] == "failed":
            continue
        run_badge = {"passed": "✅ passato", "": "⚪ in attesa"}.get(
            c["run_status"], "⚪ sconosciuto")
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
    for ds in published_datasets:
        with st.expander(f"✅ **{ds['slug']}** — fonte: {ds.get('source_id', '?')}"):
            st.write(f"**Nome:** {ds.get('name', '?')}")
            st.write(f"**Descrizione:** {ds.get('description', '?')}")

st.markdown("---")
st.caption("Dati: dataset-incubator (pipeline_signals + clean_catalog)")
data_freshness_note()
