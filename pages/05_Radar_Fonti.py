"""
Radar Fonti — salute dei portali monitorati dal Source Observatory.
Mostra lo stato GREEN/YELLOW/RED per ogni fonte, con storico e dettaglio.
"""
import streamlit as st
import altair as alt
import pandas as pd
from sources import load_radar, load_radar_history, load_sources_registry, render_sidebar_common, data_freshness_note
render_sidebar_common()

st.title("Radar fonti")

st.markdown(
    "Quali portali pubblici italiani sono online oggi. "
    "I dati vengono aggiornati giornalmente dal radar del Source Observatory."
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

# ── Trend storico ──────────────────────────────────────────────
st.subheader("Trend storico")

radar_history = load_radar_history()
probes = radar_history.get("probes", [])

if probes:
    # Costruisci DataFrame: probe_date × source_id × status
    rows = []
    for probe in probes:
        pdate = probe.get("probe_date", "?")
        for src in probe.get("sources", []):
            rows.append({
                "data": pdate,
                "fonte": src.get("id", "?"),
                "stato": src.get("status", "?"),
            })

    if rows:
        hist_df = pd.DataFrame(rows)

        # 1. Grafico a linee: conteggi per stato nel tempo
        trend = hist_df.groupby(["data", "stato"]).size().reset_index(name="conteggio")
        status_order = ["GREEN", "YELLOW", "RED"]
        trend["stato"] = pd.Categorical(trend["stato"], categories=status_order, ordered=True)
        trend = trend.sort_values(["data", "stato"])

        line_chart = alt.Chart(trend).mark_line(point=True).encode(
            x=alt.X("data:T", title="Data"),
            y=alt.Y("conteggio:Q", title="Fonti"),
            color=alt.Color(
                "stato:N",
                scale={"domain": ["GREEN", "YELLOW", "RED"],
                       "range": ["#16a34a", "#fbbf24", "#dc2626"]},
                title="Stato",
            ),
            tooltip=["data:T", "stato:N", "conteggio:Q"],
        ).properties(height=250)
        st.altair_chart(line_chart, use_container_width=True)

        # 2. Heatmap fonte × data
        heat = alt.Chart(hist_df).mark_rect().encode(
            x=alt.X("data:T", title="Data"),
            y=alt.Y("fonte:N", title="Fonte"),
            color=alt.Color(
                "stato:N",
                scale={"domain": ["GREEN", "YELLOW", "RED", "?"],
                       "range": ["#16a34a", "#fbbf24", "#dc2626", "#94a3b8"]},
                title="Stato",
            ),
            tooltip=["data:T", "fonte:N", "stato:N"],
        ).properties(height=350)
        st.altair_chart(heat, use_container_width=True)
    else:
        st.info("Nessun dato storico disponibile.")
else:
    st.info("Storico probe non ancora disponibile.")

st.markdown("---")

# ── Lista fonti ───────────────────────────────────────────────────────────────
st.subheader("Dettaglio fonti")

# Filtri
status_filter = st.selectbox(
    "Filtra per stato", ["Tutti", "GREEN", "YELLOW", "RED"]
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
        streak = (s.get("red_streak") or 0)
        d = f" · {s.get('note', '')}" if s.get("note") else ""
        st.write(f"- **{s['id']}** ({s.get('protocol', '?')}) — HTTP {s.get('http_code', '?')} — streak {streak}g{d}")

if unknown:
    with st.expander(f"⚪ Sconosciuti ({len(unknown)})"):
        for s in unknown:
            st.write(f"- **{s['id']}** — stato: {s.get('status', '?')}")

st.markdown("---")
data_freshness_note()

st.caption("Fonti: source-observatory/data/radar/radar_summary.json · radar_history.json · probe giornaliero automatico")
