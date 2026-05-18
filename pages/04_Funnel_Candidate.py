"""
Funnel candidate — flusso end-to-end SCOUTING → INTAKE → VALIDATION → PUBLISHED.

Mostra il percorso di un dataset dalla scoperta alla pubblicazione,
con tassi di conversione tra stadi e dettaglio per ogni fase.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_catalog, load_signals, load_sources_registry, load_radar

st.title("Funnel candidate")

st.markdown(
    "Flusso end-to-end dei dataset nel Lab: dalla scoperta della fonte "
    "alla pubblicazione nell'Explorer. "
    "Le barre mostrano quanti elementi passano a ogni stadio."
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
intake_candidates = []
validation_datasets = []
published_datasets = []

for sig in sigs:
    slug = sig["id"].replace("-", "_")
    if slug not in catalog_slugs:
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
        "description": ds.get("description", "")[:120],
        "updated_at": ds.get("updated_at", "?"),
    }
    if stage == "published":
        published_datasets.append(item)
    elif stage == "incubating":
        validation_datasets.append(item)

# ── Metriche funnel ───────────────────────────────────────────────────────────
n_scouting = len(scouting_sources)
n_intake = len(intake_candidates)
n_validation = len(validation_datasets)
n_published = len(published_datasets)

# Tassi di conversione
intake_rate = round(n_intake / n_scouting * 100) if n_scouting else 0
validation_rate = round(n_validation / max(n_intake, 1) * 100)
publish_rate = round(n_published / max(n_validation, 1) * 100)

col1, col2, col3, col4 = st.columns(4)
col1.metric("🔭 Scouting", n_scouting)
col2.metric("📥 Intake", n_intake, f"{intake_rate}% dello scouting")
col3.metric("🔬 Validazione", n_validation, f"{validation_rate}% intake → val.")
col4.metric("✅ Pubblicati", n_published, f"{publish_rate}% val. → pub.")

# ── Funnel visuale (barre proporzionali) ──────────────────────────────────────
st.markdown("---")
st.subheader("Panoramica")

# Calcola il massimo per proporzioni
max_n = max(n_scouting, n_intake, n_validation, n_published, 1)

# Colori e label
stages_info = [
    ("🔭 Scouting", n_scouting, "#94a3b8"),
    ("📥 Intake", n_intake, "#3b82f6"),
    ("🔬 Validazione", n_validation, "#f59e0b"),
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

# ── Tassi di conversione tra stadi ───────────────────────────────────────────
st.subheader("Tassi di conversione")

conv_df = pd.DataFrame([
    ("🔭 → 📥", "Scouting → Intake", intake_rate),
    ("📥 → 🔬", "Intake → Validazione", validation_rate),
    ("🔬 → ✅", "Validazione → Pubblicati", publish_rate),
], columns=["flusso", "descrizione", "percentuale"])

chart = alt.Chart(conv_df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusBottomLeft=5).encode(
    x=alt.X("percentuale:Q", title="Tasso di conversione (%)", scale=alt.Scale(domain=[0, 100])),
    y=alt.Y("descrizione:N", title=None, sort="-x"),
    color=alt.Color("percentuale:Q", scale=alt.Scale(scheme="blues"), legend=None),
    tooltip=["flusso", "percentuale"],
).properties(height=150)

st.altair_chart(chart, use_container_width=True)

# Insight testuale
if validation_rate < 50:
    st.info(
        f"📌 **Collo di bottiglia**: solo il {validation_rate}% dei candidate "
        "in intake arriva alla validazione. Verifica i candidate fermi in pipeline."
    )
elif publish_rate < 50:
    st.info(
        f"📌 **Collo di bottiglia**: solo il {publish_rate}% dei dataset "
        "validati viene pubblicato nell'Explorer."
    )
else:
    st.success("✅ Il funnel è bilanciato — nessun collo di bottiglia evidente.")

st.markdown("---")

# ── Dettaglio per stadio ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    [f"🔭 Scouting ({n_scouting})",
     f"📥 Intake ({n_intake})",
     f"🔬 Validazione ({n_validation})",
     f"✅ Pubblicati ({n_published})"]
)

with tab1:
    verdict_filter = st.selectbox(
        "Filtra per verdict", ["Tutti", "go", "hold"], key="scout_v"
    )
    filtered_scout = (
        scouting_sources if verdict_filter == "Tutti"
        else [s for s in scouting_sources if s["verdict"] == verdict_filter]
    )
    st.caption(f"{len(filtered_scout)} fonti mostrate")
    for src in filtered_scout:
        r = radar_map.get(src["id"], "?")
        e = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(r, "⚪")
        lbl = "→ ha candidato" if src["has_candidate"] else "in attesa"
        with st.expander(f"{e} **{src['id']}** — {src['verdict']} · {lbl}"):
            st.write(f"**Radar:** {r}")
            st.write(f"**Modalità:** {src['mode']}")
            if src["datasets"]:
                st.write(f"**Dataset in uso:** {', '.join(src['datasets'])}")

with tab2:
    st.caption("dataset.yml + pipeline CI, ma nessun clean parquet su GCS ancora")
    for c in intake_candidates:
        e = {"ok": "✅", "warn": "⚠️", "error": "❌"}.get(c["status"], "❓")
        with st.expander(f"{e} **{c['slug']}** — fonte: {c['source_id']}"):
            st.write(f"**Dettaglio:** {c['detail']}")
            st.write(f"**Ultimo run CI:** {c['last_run']}")

with tab3:
    st.caption("Clean parquet su GCS, in attesa di pubblicazione in Explorer")
    for ds in validation_datasets:
        with st.expander(f"🔬 **{ds['slug']}** — fonte: {ds['source_id']}"):
            st.write(f"**Nome:** {ds['name']}")
            st.write(f"**Descrizione:** {ds['description']}")

with tab4:
    st.caption("Clean parquet su GCS + pagina in Explorer")
    for ds in published_datasets:
        with st.expander(f"✅ **{ds['slug']}** — fonte: {ds['source_id']}"):
            st.write(f"**Nome:** {ds['name']}")
            st.write(f"**Descrizione:** {ds['description']}")

st.markdown("---")
st.caption(
    "Dati incrociati da: source-observatory (radar/registry) → "
    "dataset-incubator (pipeline_signals + clean_catalog)"
)
