"""
Radar Fonti — salute dei portali monitorati dal Source Observatory.
Mostra lo stato GREEN/YELLOW/RED per ogni fonte, con storico e dettaglio.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_radar, load_sources_registry, render_sidebar_common
render_sidebar_common()

st.title("Radar fonti")

st.markdown(
    "Salute dei portali monitorati dal Source Observatory. "
    "I dati vengono aggiornati giornalmente dal radar."
)

# ── Carica dati ───────────────────────────────────────────────────────────────
radar = load_radar()
registry = load_sources_registry()

sources = radar.get("sources", [])
status_counts = radar.get("status_counts", {})
generated_at = radar.get("generated_at", "")

# ── Metriche ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Totale fonti", radar.get("sources_total", 0))
col2.metric("🟢 GREEN", status_counts.get("GREEN", 0))
col3.metric("🟡 YELLOW", status_counts.get("YELLOW", 0))
col4.metric("🔴 RED", status_counts.get("RED", 0))

if radar.get("persistent_red", 0):
    st.warning(f"🔴 **{radar['persistent_red']} fonte/i** persistentemente RED (streak > 7 giorni)")

st.caption(f"Ultimo probe: {generated_at}")
st.markdown("---")

# ── Chart distribuzione ───────────────────────────────────────────────────────
st.subheader("Distribuzione stati")

status_df = pd.DataFrame([
    {"stato": "🟢 GREEN", "conteggio": status_counts.get("GREEN", 0)},
    {"stato": "🟡 YELLOW", "conteggio": status_counts.get("YELLOW", 0)},
    {"stato": "🔴 RED", "conteggio": status_counts.get("RED", 0)},
])

col_a, col_b = st.columns([1, 2])
with col_a:
    pie = alt.Chart(status_df).mark_arc(innerRadius=60).encode(
        theta=alt.Theta(field="conteggio", type="quantitative"),
        color=alt.Color(
            field="stato", type="nominal",
            scale={"domain": ["🟢 GREEN", "🟡 YELLOW", "🔴 RED"],
                   "range": ["#16a34a", "#fbbf24", "#dc2626"]},
        ),
        tooltip=["stato", "conteggio"],
    ).properties(width=300, height=300)
    st.altair_chart(pie)

with col_b:
    # Tabella riepilogo per protocollo
    protocol_counts = {}
    for s in sources:
        p = s.get("protocol", "?")
        protocol_counts[p] = protocol_counts.get(p, 0) + 1
    proto_df = pd.DataFrame([
        {"protocollo": p, "fonti": c}
        for p, c in sorted(protocol_counts.items(), key=lambda x: -x[1])
    ])
    st.subheader("Fonti per protocollo")
    st.dataframe(proto_df, width="stretch", hide_index=True)

st.markdown("---")

# ── Lista fonti ───────────────────────────────────────────────────────────────
st.subheader("Dettaglio fonti")

# Filtri
status_filter = st.selectbox(
    "Filtra per stato", ["Tutti", "GREEN", "YELLOW", "RED"]
)

log_filter = st.radio(
    "Filtra per ultimo probe", ["Tutte", "Oggi", "Ieri", "Più vecchio"],
    horizontal=True,
)

filtered_sources = sources
if status_filter != "Tutti":
    filtered_sources = [s for s in filtered_sources if s.get("status") == status_filter]

# Organizza per stato
green = [s for s in filtered_sources if s.get("status") == "GREEN"]
yellow = [s for s in filtered_sources if s.get("status") == "YELLOW"]
red = [s for s in filtered_sources if s.get("status") == "RED"]
unknown = [s for s in filtered_sources if s.get("status") not in ("GREEN", "YELLOW", "RED")]

st.write(f"**{len(filtered_sources)} fonti** mostrate")

with st.expander(f"🟢 GREEN ({len(green)})", expanded=len(green) > 0):
    for s in green:
        d = f" · {s.get('note', '')}" if s.get("note") else ""
        st.write(f"- **{s['id']}** ({s.get('protocol', '?')}){d}")

with st.expander(f"🟡 YELLOW ({len(yellow)})", expanded=len(yellow) > 0):
    for s in yellow:
        d = f" · {s.get('note', '')}" if s.get("note") else ""
        st.write(f"- **{s['id']}** ({s.get('protocol', '?')}) — HTTP {s.get('http_code', '?')}{d}")

with st.expander(f"🔴 RED ({len(red)})", expanded=True):
    for s in red:
        streak = s.get("red_streak", 0)
        d = f" · {s.get('note', '')}" if s.get("note") else ""
        st.write(f"- **{s['id']}** ({s.get('protocol', '?')}) — HTTP {s.get('http_code', '?')} — streak {streak}g{d}")

if unknown:
    with st.expander(f"⚪ Sconosciuti ({len(unknown)})"):
        for s in unknown:
            st.write(f"- **{s['id']}** — stato: {s.get('status', '?')}")

st.markdown("---")
data_freshness_note()

st.caption("Fonte: source-observatory/data/radar/radar_summary.json · probe giornaliero automatico")
