import streamlit as st
from utils import (
    load_rfm,
    add_rfm_segment,
    compute_segment_table,
    format_segment_table,
    compute_scenario,
    plot_scenario_chart,
    export_figure_png
)

# ------------------------------------------------
# CONFIG PAGE
# ------------------------------------------------
st.set_page_config(
    page_title="RFM - Online Retail",
    layout="wide"
)

# ===========================
#        CSS GLOBAL
# ===========================
st.markdown(
    """
    <style>

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }

    .section-bubble {
        background-color: #020617;
        border-radius: 14px;
        border: 1px solid #1f2937;
        padding: 0.5rem 0.5rem 0.5rem 0.5rem;
        margin-bottom: 1.3rem;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 1rem;
    }

    .section-pill {
        padding: 0.15rem 0.8rem;
        border-radius: 999px;
        border: 1px solid #3b4252;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: #e5e7eb;
        background: radial-gradient(circle at top left, #1d4ed8 0, #020617 60%);
        white-space: nowrap;
    }

    .section-title {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #e5e7eb !important;
        margin: 0;
        padding: 0;
    }

    .kpi-card {
        background-color: #111827;
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid #3b4252;
        text-align:center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.25);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------
# DATA
# ------------------------------------------------
df_rfm = load_rfm()
df_rfm = add_rfm_segment(df_rfm)

# ------------------------------------------------
# SIDEBAR
# ------------------------------------------------
with st.sidebar:
    st.header("Paramètres business")
    taux_marge = st.slider("Taux de marge (%)", 0, 100, 30, 1) / 100

# ------------------------------------------------
# SECTION : TABLE RFM
# ------------------------------------------------
st.markdown("""
<div class="section-bubble">
    <div class="section-header">
        <div class="section-pill">Segmentation</div>
        <div class="section-title">📊 Table RFM par segment</div>
    </div>
""", unsafe_allow_html=True)

seg_table = compute_segment_table(df_rfm, taux_marge)
display_df = format_segment_table(seg_table, df_rfm)

st.dataframe(display_df, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------
# SECTION : SCÉNARIOS
# ------------------------------------------------
st.markdown("""
<div class="section-bubble">
    <div class="section-header">
        <div class="section-pill">Scénarios CRM</div>
        <div class="section-title">🚀 Simulation d'activation</div>
    </div>
""", unsafe_allow_html=True)

col_seg, col_p, col_u = st.columns(3)

segment_cible = col_seg.selectbox("Segment ciblé", options=seg_table['Segment'].unique())
part_clients = col_p.slider("Part de clients activés (%)", 0, 100, 50, 5)
uplift_ca = col_u.slider("Uplift de CA (%)", 0, 200, 20, 5)

seg_row = seg_table[seg_table['Segment'] == segment_cible].iloc[0]
results = compute_scenario(seg_row, taux_marge, part_clients, uplift_ca)

# CHART
st.subheader("Répartition du CA : base + CA additionnel (k€)")

col_l, col_center, col_r = st.columns([1, 2, 1])

with col_center:
    fig = plot_scenario_chart(results["ca_base"], results["ca_incremental"])
    st.pyplot(fig)

    # Export
    buffer = export_figure_png(fig)
    st.download_button(
        label="📥 Télécharger le graphique (PNG)",
        data=buffer,
        file_name=f"scenario_{segment_cible}.png",
        mime="image/png"
    )

# KPI
st.subheader(f"Résultats pour le segment {segment_cible}")

c1, c2, c3 = st.columns(3)
c1.metric("CA base", f"{results['ca_base']:,.0f}")
c2.metric("CA additionnel", f"{results['ca_incremental']:,.0f}")
c3.metric("CA nouveau", f"{results['ca_nouveau']:,.0f}")

d1, d2 = st.columns(2)
d1.metric("Marge base", f"{results['marge_base']:,.0f}")
d2.metric("Marge additionnelle", f"{results['marge_incrementale']:,.0f}")

st.markdown("</div>", unsafe_allow_html=True)
