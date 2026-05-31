"""Pipeline candidate — funnel intake → analisi pubblica, salute CI, dettaglio."""
import streamlit as st

from sources import (
    data_freshness_note,
    load_analysis_registry,
    load_catalog,
    load_explorer_datasets,
    load_signals,
)

# ── Mapping dataset → Explorer → Analisi (dinamico) ──────────────────────────
# I dataset su Explorer e le analisi vengono caricati live da upstream.
# Lo SLUG_MAP serve per i pochi dataset con nome diverso tra DI e DE.
_SLUG_MAP = {
    "aifa_spesa_consumo": "spesa-farmaceutica",
    "ispra_ru_base": "rifiuti-urbani",
    "civile_flussi": "flussi-giustizia-civile",
    "terna_capacita_rinnovabile": "capacita-rinnovabile",
    "terna_electricity_by_source": "produzione-elettrica-fonti",
    "bdap_entrate_stato": "entrate-stato",
    "inps_pensioni_trimestrale": "pensioni-inps",
}

def _de_slug(di_slug: str) -> str:
    return _SLUG_MAP.get(di_slug, di_slug.replace("_", "-"))

st.title("⚙️ Pipeline candidate")

st.markdown(
    "Pipeline dei dataset del Lab: "
    "dal candidate (dataset.yml + CI) alla pubblicazione in Explorer "
    "fino all'analisi pubblica su dataciviclab.org. "
    "Funnel end-to-end e dettaglio operativo in una vista."
)

# ── Carica dati ───────────────────────────────────────────────────────────────
signals = load_signals()
catalog = load_catalog()

sigs = signals.get("signals", [])
datasets = catalog.get("datasets", [])

# Carica Explorer e Analisi per il funnel end-to-end
explorer_slugs = load_explorer_datasets()
analysis_map = load_analysis_registry()  # {analysis_slug: dataset_slug}
analysis_dataset_slugs = set(analysis_map.values())  # dataset con analisi

catalog_slugs = set(ds["slug"] for ds in datasets)

# ── Indice segnali per slug (per lookup run) ──────────────────────────────────
signals_by_slug: dict[str, dict] = {}
for sig in sigs:
    sig_slug = sig["id"].replace("-", "_")
    signals_by_slug[sig_slug] = sig

# ── Classifica candidate ──────────────────────────────────────────────────────
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
    slug = ds["slug"]
    sig_data = signals_by_slug.get(slug, {})
    sr = sig_data.get("sample_run", {}) or {}
    item = {
        "slug": slug,
        "name": ds.get("name", ""),
        "source_id": ds.get("source_id", "?"),
        "description": ds.get("description", "")[:120],
        "on_explorer": _de_slug(slug) in explorer_slugs,
        "has_analysis": slug in analysis_dataset_slugs,
        "run_status": sr.get("status", ""),
        "run_url": sr.get("run_url", ""),
        "checked_at": sr.get("checked_at", ""),
    }
    if stage == "published":
        published_datasets.append(item)
    elif stage == "incubating":
        incubazione.append(item)

# Elenco completo di tutti i segnali con run falliti (candidate + catalogo)
all_failed = []
for sig in sigs:
    sr = sig.get("sample_run", {}) or {}
    if sr.get("status") == "failed":
        slug = sig["id"].replace("-", "_")
        all_failed.append({
            "slug": slug,
            "id": sig["id"],
            "label": sig.get("label", slug),
            "source_id": sig.get("source_id", "?"),
            "detail": sig.get("detail", ""),
            "checked_at": sr.get("checked_at", "?"),
            "run_url": sr.get("run_url", ""),
            "in_catalogo": slug in catalog_slugs,
        })

n_intake = len(candidati)
n_validation = len(incubazione)
n_published = len(published_datasets)
n_explorer = sum(1 for d in published_datasets if d["on_explorer"])
n_analisi = sum(1 for d in published_datasets if d["has_analysis"])
n_failed = len(all_failed)
n_compose = sum(1 for c in candidati if c["tipo"] == "compose")

# ── Funnel ─────────────────────────────────────────────────────────────────
st.subheader("Funnel pipeline")

ok_count = sum(1 for s in sigs if s.get("status") == "ok")
warn_count = sum(1 for s in sigs if s.get("status") == "warn")
err_count = sum(1 for s in sigs if s.get("status") == "error")
run_passed = sum(1 for s in sigs if s.get("sample_run", {}).get("status") == "passed")
run_failed = sum(1 for s in sigs if s.get("sample_run", {}).get("status") == "failed")
run_none = len(sigs) - run_passed - run_failed

max_n = max(n_intake, n_validation, n_published, 1)
stages = [
    ("📥 Intake", n_intake, "#94a3b8", f"{n_compose} compose"),
    ("🔬 Incubazione", n_validation, "#3b82f6", ""),
    ("✅ Pubblicati", n_published, "#16a34a", ""),
    ("🌐 Su Explorer", n_explorer, "#8b5cf6", ""),
    ("📄 Con analisi", n_analisi, "#ec4899", ""),
]
for label, count, color, note in stages:
    pct = count / max_n if max_n else 0
    r0, r1 = st.columns([2.5, 12])
    with r0:
        st.write(f"**{label}**")
    with r1:
        note_html = (
            f"<span style='font-size:0.85em;color:gray;'> · {note}</span>"
            if note else ""
        )
        bar_html = f"""
        <div style="border-radius:8px; height:32px; overflow:hidden;">
            <div style="background:{color}; width:{pct*100:.0f}%; height:100%;
                border-radius:8px; display:flex; align-items:center; padding-left:10px;">
                <span style="font-weight:bold; font-size:16px;">{count}{note_html}</span>
            </div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)

# Metriche in full width sotto
col1, col2, col3, col4 = st.columns(4)
col1.metric("✅ Segnali OK", ok_count, "configurazione valida")
col2.metric("🏃 Run passati", run_passed, f"{run_passed}/{ok_count} segnali")
col3.metric("❌ Run falliti", run_failed,
            f"{round(run_failed/(run_passed+run_failed)*100)}% dei run"
            if run_failed else "nessuno")
col4.metric("⏳ Mai eseguiti", run_none, "senza run CI")

st.markdown("---")

# ── Dettaglio per tab ─────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    f"📋 Da rivedere ({n_failed})",
    f"🔬 In corso ({n_intake + n_validation - n_failed})",
    f"✅ Completati ({n_published})",
])

with tab1:
    if all_failed:
        for f in all_failed:
            badge = "🧩 compose" if f["id"].startswith("compose:") else ""
            cat = "📦 in catalogo" if f["in_catalogo"] else "📥 candidate"
            parts = [f"❌ **{f['label']}** — {f['source_id']}", cat]
            if badge:
                parts.append(badge)
            with st.expander(" · ".join(parts)):
                st.write(f"**Dettaglio:** {f['detail']}")
                st.write(f"**Ultimo check:** {f['checked_at']}")
                st.write("**Ultimo run:** ❌ fallito")
                if f["run_url"]:
                    st.write(f"**Run CI:** [{f['run_url']}]({f['run_url']})")
    else:
        st.success("Nessun run fallito.")

with tab2:
    # Candidate intake (non falliti)
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
        badges = []
        if ds["on_explorer"]:
            badges.append("🌐 Explorer")
        if ds["has_analysis"]:
            badges.append("📄 Analisi")
        badge_str = " · ".join(badges) if badges else "—"
        with st.expander(f"✅ **{ds['slug']}** — {badge_str}"):
            st.write(f"**Nome:** {ds.get('name', '?')}")
            st.write(f"**Descrizione:** {ds.get('description', '?')}")

            run_badge = {"passed": "✅ passato", "failed": "❌ fallito",
                         "": "⚪ sconosciuto"}.get(ds["run_status"], "⚪ sconosciuto")
            st.write(f"**Ultimo run:** {run_badge}")
            if ds["checked_at"]:
                st.write(f"**Check:** {ds['checked_at']}")
            if ds["run_url"]:
                st.write(f"**Run CI:** [{ds['run_url']}]({ds['run_url']})")

            if ds["on_explorer"]:
                de = _de_slug(ds["slug"])
                st.write(f"🌐 **Explorer:** "
                         f"[{de}](https://dataciviclab.github.io/data-explorer/dataset/{de})")
            if ds["has_analysis"]:
                for a_slug, d_slug in analysis_map.items():
                    if d_slug == ds["slug"]:
                        st.write(f"📄 **Analisi:** "
                                 f"[{a_slug}](https://dataciviclab.org/analisi/{a_slug})")
                        break

st.markdown("---")
st.caption("Dati: dataset-incubator (pipeline_signals + clean_catalog)")
data_freshness_note()
