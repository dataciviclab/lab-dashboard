"""
Funnel candidate — flusso end-to-end SCOUTING → INTAKE → VALIDATION → PUBLISHED.

Mostra il percorso di un dataset dalla scoperta alla pubblicazione,
con tassi di conversione tra stadi e dettaglio per ogni fase.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_catalog, load_signals, load_sources_registry, load_radar, load_catalog_signals, render_sidebar_common, data_freshness_note
render_sidebar_common()

st.title("Funnel candidate")

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
catalog_signals = load_catalog_signals()

datasets = catalog.get("datasets", [])
sigs = signals.get("signals", [])
radar_sources = radar.get("sources", [])
signals_map = {}
for sig in catalog_signals.get("signals", []):
    src_id = sig.get("source", "")
    signals_map[src_id] = sig

# ── Costruisci i quattro stadi ────────────────────────────────────────────────

# 1. SCOUTING
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

# 2. INTAKE / VALIDAZIONE / PUBBLICATI
catalog_slugs = set(ds["slug"] for ds in datasets)
candidati = []
incubazione = []
published_datasets = []

for sig in sigs:
    slug = sig["id"].replace("-", "_")
    if slug not in catalog_slugs:
        candidati.append({
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
        "description": ds.get("description", "")[:120],
        "source_desc": ds.get("source", ""),
    }
    if stage == "published":
        published_datasets.append(item)
    elif stage == "incubating":
        incubazione.append(item)

# ── Metriche funnel ───────────────────────────────────────────────────────────
n_scouting = len(scouting_sources)
n_intake = len(candidati)
n_validation = len(incubazione)
n_published = len(published_datasets)

src_to_intake = round(n_intake / n_scouting * 100) if n_scouting else 0
val_to_pub = round(n_published / max(n_validation, 1) * 100)

col1, col2, col3, col4 = st.columns(4)
active_scout = sum(1 for s in scouting_sources if not s["has_candidate"] and s["verdict"] == "go")
n_with_signal = sum(1 for sig in signals_map.values()
                    if sig.get("suggested_action") in ("catalog-watch-ready", "low signal"))
col1.metric("🔭 Fonti monitorate", n_scouting,
            f"{active_scout} in esplorazione · {n_with_signal} con segnale")
col2.metric("📥 Candidati", n_intake, f"{src_to_intake}% delle fonti")
col3.metric("🔬 Incubazione", n_validation)
col4.metric("✅ Pubblicati", n_published, f"{val_to_pub}% dei validati")

# ── Funnel visuale (barre proporzionali) ──────────────────────────────────────
st.markdown("---")
st.subheader("Panoramica")

# Calcola il massimo per proporzioni
max_n = max(n_scouting, n_intake, n_validation, n_published, 1)

# Colori e label
stages_info = [
    ("🔭 Fonti monitorate", n_scouting, "#94a3b8"),
    ("📥 Candidati", n_intake, "#3b82f6"),
    ("🔬 Incubazione", n_validation, "#f59e0b"),
    ("✅ Pubblicati", n_published, "#16a34a"),
]

# Mostra barre proporzionali con st.progress
for label, count, color in stages_info:
    pct = count / max_n
    pct_display = round(pct * 100)

    cols = st.columns([2, 12])
    with cols[0]:
        st.write(f"**{label}**")
    with cols[1]:
        # Barra personalizzata con HTML
        bar_html = f"""
        <div class="funnel-bar-bg" style="border-radius:8px; height:32px; overflow:hidden;">
            <div class="funnel-bar-fill" style="background:{color}; width:{pct_display}%; height:100%; border-radius:8px; display:flex; align-items:center; padding-left:10px;">
                <span style="font-weight:bold; font-size:16px;">{count}</span>
            </div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "ℹ️ Gli stadi non sono una sequenza lineare stretta — "
    "alcuni dataset in validazione arrivano da support datasets "
    "che non passano dall'intake."
)

st.markdown("---")

# ── Dettaglio per stadio ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    [f"🔭 Fonti monitorate ({n_scouting})",
     f"📥 Candidati ({n_intake})",
     f"🔬 Incubazione ({n_validation})",
     f"✅ Pubblicati ({n_published})"]
)

with tab1:
    col_v, col_s = st.columns(2)
    with col_v:
        verdict_filter = st.selectbox(
            "Filtra per verdict", ["Tutti", "go", "hold"], key="scout_v"
        )
    with col_s:
        signal_actions = ["Tutti", "catalog-watch-ready", "low signal", "nessuna"]
        signal_filter = st.selectbox(
            "Filtra per segnale inventariale", signal_actions, key="scout_sig"
        )

    filtered_scout = scouting_sources
    if verdict_filter != "Tutti":
        filtered_scout = [s for s in filtered_scout if s["verdict"] == verdict_filter]
    if signal_filter != "Tutti":
        filtered_scout = [
            s for s in filtered_scout
            if signals_map.get(s["id"], {}).get("suggested_action") == signal_filter
        ]

    n_scout_candidate = sum(1 for s in filtered_scout if s['has_candidate'])
    n_scout_exploring = sum(1 for s in filtered_scout if not s['has_candidate'] and s['verdict']=='go')
    n_scout_signaled = sum(1 for s in filtered_scout
                           if signals_map.get(s["id"], {}).get("suggested_action") in ("catalog-watch-ready", "low signal"))
    st.caption(
        f"{len(filtered_scout)} fonti mostrate · "
        f"{n_scout_candidate} con dataset · "
        f"{n_scout_exploring} in esplorazione · "
        f"{n_scout_signaled} con segnale inventariale"
    )
    for src in filtered_scout:
        r = radar_map.get(src["id"], "?")
        e = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(r, "⚪")
        lbl = "→ ha candidato" if src["has_candidate"] else "in attesa"

        # Segnale inventariale
        sig = signals_map.get(src["id"], {})
        sig_action = sig.get("suggested_action", "?")
        sig_metric = sig.get("metric_value", "")
        sig_topics = sig.get("topics", {})
        topics_str = ", ".join(f"{k}={v}" for k, v in sig_topics.items()) if sig_topics else ""
        sig_badge = {
            "catalog-watch-ready": "📡 pronto",
            "low signal": "📡 segnale debole",
            "nessuna": "",
        }.get(sig_action, sig_action)

        expander_title = f"{e} **{src['id']}** — {src['verdict']} · {lbl}"
        if sig_badge:
            expander_title += f" · {sig_badge}"
        with st.expander(expander_title):
            st.write(f"**Radar:** {r}")
            st.write(f"**Modalità:** {src['mode']}")
            if sig:
                st.write(f"**Segnale:** {sig_action} · {sig_metric} item" if sig_metric else f"**Segnale:** {sig_action}")
                if topics_str:
                    st.write(f"**Topic rilevati:** {topics_str}")
                if sig.get("years_range"):
                    st.write(f"**Copertura anni:** {sig['years_range'][0]}–{sig['years_range'][1]}")
            if src["datasets"]:
                st.write(f"**Dataset in uso:** {', '.join(src['datasets'])}")

with tab2:
    st.caption("dataset.yml + pipeline CI, ma nessun clean parquet su GCS ancora")
    for c in candidati:
        e = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(c["status"], "❓")
        with st.expander(f"{e} **{c['slug']}** — fonte: {c['source_id']}"):
            st.write(f"**Dettaglio:** {c['detail']}")
            st.write(f"**Ultimo run CI:** {c['last_run']}")

with tab3:
    st.caption("Clean parquet su GCS, in attesa di pubblicazione in Explorer")
    for ds in incubazione:
        with st.expander(f"🔬 **{ds['slug']}** — fonte: {ds['source_id']}"):
            st.write(f"**Nome:** {ds['name']}")
            st.write(f"**Descrizione:** {ds['description']}")

with tab4:
    st.caption("Clean parquet su GCS + pagina in Explorer")
    for ds in published_datasets:
        with st.expander(f"✅ **{ds['slug']}** — fonte: {ds.get('source_id', '?')}"):
            st.write(f"**Nome:** {ds.get('name', '?')}")
            st.write(f"**Descrizione:** {ds.get('description', '?')}")
            if ds.get("source_desc"):
                st.write(f"**Fonte descrizione:** {ds['source_desc']}")

st.markdown("---")
st.caption(
    "Dati incrociati da: source-observatory (radar/registry/catalog_signals) → "
    "dataset-incubator (pipeline_signals + clean_catalog)"
)
data_freshness_note()
