"""
Funnel candidate — flusso end-to-end SCOUTING → INTAKE → VALIDATION → PUBLISHED.

Ogni stadio mostra:
  - Quanti elementi ci sono
  - Elenco dettagliato con expander
  - Cross-ref con la fonte upstream
"""
import streamlit as st
import altair as alt
import pandas as pd
from lib.sources import load_catalog, load_signals, load_sources_registry, load_radar

st.title("Funnel candidate")

st.markdown(
    "Flusso end-to-end dei dataset nel Lab: dalla scoperta della fonte "
    "alla pubblicazione nell'Explorer."
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

# 1. SCOUTING: fonti monitorate che non hanno ancora candidati in pipeline
#    (o hanno verdict=hold)
candidate_source_ids = set()
for sig in sigs:
    if sig.get("source_id"):
        candidate_source_ids.add(sig["source_id"])

# Aggiungi source_id dai dataset pubblicati/incubating
for ds in datasets:
    if ds.get("source_id"):
        candidate_source_ids.add(ds["source_id"])

scouting_sources = []
for src_id, src_data in registry.items():
    verdict = src_data.get("verdict", "?")
    obs_mode = src_data.get("observation_mode", "?")
    datasets_in_use = src_data.get("datasets_in_use", [])
    # Una fonte è "in scouting" se non ha ancora candidati in pipeline
    has_candidate = src_id in candidate_source_ids
    scouting_sources.append({
        "id": src_id,
        "verdict": verdict,
        "mode": obs_mode,
        "has_candidate": has_candidate,
        "datasets": datasets_in_use,
    })

# Radar status lookup
radar_map = {s["id"]: s["status"] for s in radar_sources}

# 2. INTAKE: candidate in pipeline_signals ma NON in clean_catalog (no clean parquet)
signal_ids = set()
for sig in sigs:
    signal_ids.add(sig["id"])  # pipeline_signals usa trattini

catalog_slugs = set(ds["slug"] for ds in datasets)  # clean_catalog usa underscore

# Normalizza: pipeline_signals id -> slug (sostituisci trattini con underscore)
intake_candidates = []
validation_datasets = []
published_datasets = []

for sig in sigs:
    slug = sig["id"].replace("-", "_")
    if slug not in catalog_slugs:
        # In intake: ha dataset.yml e CI, ma non ha ancora clean parquet
        intake_candidates.append({
            "slug": slug,
            "id": sig["id"],
            "source_id": sig.get("source_id", "?"),
            "status": sig.get("status", "?"),
            "detail": sig.get("detail", ""),
            "last_run": sig.get("sample_run", {}).get("checked_at", "?"),
        })

for ds in datasets:
    stage = ds.get("stage", "")
    item = {
        "slug": ds["slug"],
        "name": ds.get("name", ""),
        "source_id": ds.get("source_id", "?"),
        "description": ds.get("description", "")[:100],
        "updated_at": ds.get("updated_at", "?"),
    }
    if stage == "published":
        published_datasets.append(item)
    elif stage == "incubating":
        validation_datasets.append(item)
    # else: skip deprecated

# ── Mostra funnel ─────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("🔭 Scouting", len(scouting_sources),
            help="Fonti monitorate dal Source Observatory")
col2.metric("📥 Intake", len(intake_candidates),
            help="Candidate con dataset.yml, senza clean parquet")
col3.metric("🔬 Validazione", len(validation_datasets),
            help="Clean parquet su GCS, non ancora in Explorer")
col4.metric("✅ Pubblicati", len(published_datasets),
            help="Clean parquet + pagina in Explorer")

# ── Barre del funnel ──────────────────────────────────────────────────────────
st.markdown("---")

funnel_df = pd.DataFrame([
    {"stadio": "🔭 Scouting", "conteggio": len(scouting_sources)},
    {"stadio": "📥 Intake", "conteggio": len(intake_candidates)},
    {"stadio": "🔬 Validazione", "conteggio": len(validation_datasets)},
    {"stadio": "✅ Pubblicati", "conteggio": len(published_datasets)},
])

# Funnel chart (barre orizzontali decrescenti)
chart = alt.Chart(funnel_df).mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
    y=alt.Y("stadio:N", title=None, sort="-x"),
    x=alt.X("conteggio:Q", title="Numero"),
    color=alt.Color("stadio:N", legend=None,
                     scale={"domain": funnel_df["stadio"].tolist(),
                            "range": ["#94a3b8", "#3b82f6", "#f59e0b", "#16a34a"]}),
    tooltip=["stadio", "conteggio"],
).properties(height=250)

st.altair_chart(chart, use_container_width=True)

st.markdown("---")

# ── Dettaglio per stadio ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["🔭 Scouting", "📥 Intake", "🔬 Validazione", "✅ Pubblicati"]
)

with tab1:
    st.subheader(f"Fonti in scouting ({len(scouting_sources)})")

    # Filtri
    verdict_filter = st.selectbox(
        "Filtra per verdict",
        ["Tutti", "go", "hold"],
        key="scout_verdict",
    )
    filtered_scout = scouting_sources
    if verdict_filter != "Tutti":
        filtered_scout = [s for s in filtered_scout if s["verdict"] == verdict_filter]

    st.write(f"**{len(filtered_scout)} fonti** mostrate")

    for src in filtered_scout:
        radar_status = radar_map.get(src["id"], "?")
        emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(radar_status, "⚪")
        candidate_label = "→ ha candidato" if src["has_candidate"] else "in attesa"
        with st.expander(f"{emoji} **{src['id']}** — {src['verdict']} · {candidate_label}"):
            st.write(f"**Modalità:** {src['mode']}")
            st.write(f"**Verdict:** {src['verdict']}")
            st.write(f"**Radar:** {radar_status}")
            if src["datasets"]:
                st.write(f"**Dataset in uso:** {', '.join(src['datasets'])}")

with tab2:
    st.subheader(f"Candidate in intake ({len(intake_candidates)})")
    st.caption("Ha dataset.yml e pipeline CI, ma non ha ancora clean parquet su GCS")

    for cand in intake_candidates:
        emoji = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(cand["status"], "❓")
        with st.expander(f"{emoji} **{cand['slug']}** — fonte: {cand['source_id']}"):
            st.write(f"**ID pipeline:** {cand['id']}")
            st.write(f"**Fonte:** {cand['source_id']}")
            st.write(f"**Dettaglio:** {cand['detail']}")
            st.write(f"**Ultimo run CI:** {cand['last_run']}")

with tab3:
    st.subheader(f"Dataset in validazione ({len(validation_datasets)})")
    st.caption("Clean parquet su GCS, in attesa di pubblicazione in Explorer")

    for ds in validation_datasets:
        with st.expander(f"🔬 **{ds['slug']}** — fonte: {ds['source_id']}"):
            st.write(f"**Nome:** {ds['name']}")
            st.write(f"**Descrizione:** {ds['description']}")
            st.write(f"**Fonte:** {ds['source_id']}")

with tab4:
    st.subheader(f"Dataset pubblicati ({len(published_datasets)})")
    st.caption("Clean parquet su GCS + pagina in Explorer")

    for ds in published_datasets:
        with st.expander(f"✅ **{ds['slug']}** — fonte: {ds['source_id']}"):
            st.write(f"**Nome:** {ds['name']}")
            st.write(f"**Descrizione:** {ds['description']}")
            st.write(f"**Ultimo aggiornamento:** {ds['updated_at']}")

st.markdown("---")
st.caption(
    "Dati incrociati da: source-observatory (radar/registry) → "
    "dataset-incubator (pipeline_signals + clean_catalog)"
)
