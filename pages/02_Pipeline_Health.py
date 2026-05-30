"""Pipeline candidate — funnel intake → pubblicazione, salute CI, dettaglio operativo."""
import streamlit as st

from sources import data_freshness_note, load_catalog, load_signals

st.title("⚙️ Pipeline candidate")

st.markdown(
    "Pipeline dei dataset del Lab: "
    "dal candidate (dataset.yml + CI) alla pubblicazione in Explorer. "
    "Funnel, salute run CI e dettaglio operativo in una vista."
)

# ── Carica dati ───────────────────────────────────────────────────────────────
signals = load_signals()
catalog = load_catalog()

sigs = signals.get("signals", [])
datasets = catalog.get("datasets", [])

catalog_slugs = set(ds["slug"] for ds in datasets)

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
    ("📥 Intake", n_intake, "#3b82f6", f"{n_compose} compose"),
    ("🔬 Incubazione", n_validation, "#f59e0b", ""),
    ("✅ Pubblicati", n_published, "#16a34a", ""),
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
        with st.expander(f"✅ **{ds['slug']}** — fonte: {ds.get('source_id', '?')}"):
            st.write(f"**Nome:** {ds.get('name', '?')}")
            st.write(f"**Descrizione:** {ds.get('description', '?')}")

st.markdown("---")
st.caption("Dati: dataset-incubator (pipeline_signals + clean_catalog)")
data_freshness_note()
