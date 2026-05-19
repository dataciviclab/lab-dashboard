"""
Funnel candidate — flusso end-to-end SCOUTING → INTAKE → VALIDATION → PUBLISHED.
Mostra il percorso di un dataset dalla scoperta alla pubblicazione,
con focus sulle azioni: cosa va rivisto, cosa è in corso, cosa è stato pubblicato.
"""
import streamlit as st
from sources import load_catalog, load_signals, load_sources_registry, load_radar, data_freshness_note
st.title("📥 Funnel candidate")

st.markdown(
    "Come un dato pubblico diventa un dataset del Lab: "
    "dalla scoperta della fonte alla pubblicazione nell'Explorer. "
    "Ogni stadio è indipendente — un dataset può entrare in validazione "
    "anche senza passare dall'intake (es. support datasets)."
)

# ── Carica tutti i dati ───────────────────────────────────────────────────────
catalog = load_catalog()
signals = load_signals()
registry = load_sources_registry()
radar = load_radar()

datasets = catalog.get("datasets", [])
sigs = signals.get("signals", [])
radar_sources = radar.get("sources", [])

# ── Costruisci i quattro stadi ────────────────────────────────────────────────
candidate_source_ids = set()
for sig in sigs:
    if sig.get("source_id"):
        candidate_source_ids.add(sig["source_id"])
for ds in datasets:
    if ds.get("source_id"):
        candidate_source_ids.add(ds["source_id"])

scouting_sources = []
for src_id, src_data in registry.items():
    scouting_sources.append({
        "id": src_id,
        "verdict": src_data.get("verdict", "?"),
        "mode": src_data.get("observation_mode", "?"),
        "has_candidate": src_id in candidate_source_ids,
        "datasets": src_data.get("datasets_in_use", []),
    })

radar_map = {s["id"]: s["status"] for s in radar_sources}

catalog_slugs = set(ds["slug"] for ds in datasets)
candidati = []
incubazione = []
published_datasets = []

for sig in sigs:
    slug = sig["id"].replace("-", "_")
    if slug not in catalog_slugs:
        sr = sig.get("sample_run", {}) or {}
        tipo = "compose" if sig["id"].startswith("compose:") else "candidate"
        candidati.append({
            "slug": slug,
            "id": sig["id"],
            "source_id": sig.get("source_id", "?"),
            "status": sig.get("status", "?"),
            "detail": sig.get("detail", ""),
            "checked_at": sr.get("checked_at", "?"),
            "run_url": sr.get("run_url", ""),
            "run_status": sr.get("status", ""),
            "tipo": tipo,
        })

for ds in datasets:
    stage = ds.get("stage", "")
    item = {
        "slug": ds["slug"],
        "name": ds.get("name", ""),
        "source_id": ds.get("source_id", "?"),
        "description": ds.get("description", "")[:120],
        "source_desc": ds.get("source", ""),
    }
    if stage == "published":
        published_datasets.append(item)
    elif stage == "incubating":
        incubazione.append(item)

# ── Conteggi ──────────────────────────────────────────────────────────────────
n_scouting = len(scouting_sources)
n_intake = len(candidati)
n_validation = len(incubazione)
n_published = len(published_datasets)

run_failed_candidates = [c for c in candidati if c["run_status"] == "failed"]
n_failed = len(run_failed_candidates)
n_compose = sum(1 for c in candidati if c["tipo"] == "compose")
active_scout = sum(1 for s in scouting_sources
                   if not s["has_candidate"] and s["verdict"] == "go")

# ══════════════════════════════════════════════════════════════════
# FUNNEL UNIFICATO
# ══════════════════════════════════════════════════════════════════
st.subheader("Pipeline")

max_n = max(n_scouting, n_intake, n_validation, n_published, 1)
stages = [
    ("🔭 Scouting", n_scouting, "#94a3b8", f"{active_scout} in esplorazione"),
    ("📥 Intake", n_intake, "#3b82f6", f"{n_compose} compose"),
    ("🔬 Incubazione", n_validation, "#f59e0b", ""),
    ("✅ Pubblicati", n_published, "#16a34a", ""),
]

for label, count, color, note in stages:
    pct = count / max_n
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

st.caption(
    "ℹ️ Gli stadi non sono una sequenza lineare stretta — "
    "alcuni dataset in validazione arrivano da support datasets "
    "che non passano dall'intake."
)

# Alert
if n_failed:
    st.error(f"❌ **{n_failed} candidate con run fallito** — da rivedere")
if run_failed_candidates:
    details = " · ".join(f"`{c['slug']}`" for c in run_failed_candidates)
    st.caption(f"Coinvolti: {details}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# 3 SEZIONI PER AZIONE
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    f"📋 Da rivedere ({n_failed + active_scout})",
    f"🔬 In corso ({n_intake + n_validation})",
    f"✅ Completati ({n_published})",
])

with tab1:
    """Candidate con problemi o fonti ancora da esplorare."""
    if n_failed:
        st.markdown("**❌ Candidate con run fallito**")
        for c in run_failed_candidates:
            run_badge = "❌ fallito"
            with st.expander(f"❌ **{c['slug']}** — fonte: {c['source_id']}"):
                st.write(f"**Dettaglio:** {c['detail']}")
                st.write(f"**Ultimo check:** {c['checked_at']}")
                st.write(f"**Ultimo run:** {run_badge}")
                if c["run_url"]:
                    st.write(f"**Link CI:** [{c['run_url']}]({c['run_url']})")
                tag = "🧩 compose" if c["tipo"] == "compose" else "📥 candidate"
                st.caption(tag)

    if active_scout:
        st.markdown("**🔭 Fonti in esplorazione (verdict go, nessun candidate)**")
        for src in scouting_sources:
            if src["verdict"] == "go" and not src["has_candidate"]:
                r = radar_map.get(src["id"], "?")
                e = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(r, "⚪")
                with st.expander(f"{e} **{src['id']}** — {src['mode']}"):
                    st.write(f"**Radar:** {r}")
                    st.write(f"**Modalità:** {src['mode']}")

    if not n_failed and not active_scout:
        st.success("Niente da rivedere — tutto in regola.")

with tab2:
    """Candidate in corso e dataset in incubazione."""
    st.markdown(f"**📥 Candidate intake ({n_intake})**")
    st.caption("dataset.yml + pipeline CI, ma nessun clean parquet su GCS ancora")

    for c in candidati:
        if c["run_status"] == "failed":
            continue
        run_badge = {"passed": "✅ passato", "failed": "❌ fallito", "": "⚪ in attesa"}.get(
            c["run_status"], "⚪ sconosciuto"
        )
        e = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(c["status"], "❓")
        tag = "🧩 compose" if c["tipo"] == "compose" else ""
        title = f"{e} **{c['slug']}** — run: {run_badge}"
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
    st.caption("Clean parquet su GCS + pagina in Explorer")
    for ds in published_datasets:
        with st.expander(f"✅ **{ds['slug']}** — fonte: {ds.get('source_id', '?')}"):
            st.write(f"**Nome:** {ds.get('name', '?')}")
            st.write(f"**Descrizione:** {ds.get('description', '?')}")
            if ds.get("source_desc"):
                st.write(f"**Fonte descrizione:** {ds['source_desc']}")

st.markdown("---")
st.caption(
    "Dati incrociati da: source-observatory (sources_registry) → "
    "dataset-incubator (pipeline_signals + clean_catalog)"
)
data_freshness_note()
