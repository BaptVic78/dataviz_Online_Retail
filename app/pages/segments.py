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

st.set_page_config(page_title="RFM - Online Retail", layout="wide")
st.title("Tableau de bord RFM - Clients & Scénarios CRM")

# --- Chargement ---
df_rfm = load_rfm()
df_rfm = add_rfm_segment(df_rfm)

# --- Paramètres ---
st.sidebar.header("Paramètres business")
taux_marge = st.sidebar.slider("Taux de marge (%)", 0, 100, 30, 1) / 100

# --- Table RFM ---
seg_table = compute_segment_table(df_rfm, taux_marge)
display_df = format_segment_table(seg_table, df_rfm)

st.subheader("Table RFM par segment")
st.dataframe(display_df, use_container_width=True)

# ======================
# SCÉNARIOS
# ======================
st.markdown("---")
st.subheader("Scénarios CRM - Simulation d'activation")

col_seg, col_p, col_u = st.columns(3)
segment_cible = col_seg.selectbox("Segment ciblé", options=seg_table['Segment'].unique())
part_clients = col_p.slider("Part de clients activés (%)", 0, 100, 50, 5)
uplift_ca = col_u.slider("Uplift de CA (%)", 0, 200, 20, 5)

seg_row = seg_table[seg_table['Segment'] == segment_cible].iloc[0]
results = compute_scenario(seg_row, taux_marge, part_clients, uplift_ca)

st.subheader("Répartition du CA : base + CA additionnel (k€)")

col_l, col_center, col_r = st.columns([1, 2, 1])

with col_center:
    ca_chart = plot_scenario_chart(results["ca_base"], results["ca_incremental"])
    st.pyplot(ca_chart)

    buffer = export_figure_png(ca_chart)
    st.download_button(
        label="📥 Télécharger le graphique (PNG)",
        data=buffer,
        file_name=f"graphique_scenario_{segment_cible}.png",
        mime="image/png"
    )


# --- Résultats ---
st.subheader(f"Résultats pour le segment {segment_cible}")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("CA base", f"{results['ca_base']:,.0f}")
with c2:
    st.metric("CA additionnel", f"{results['ca_incremental']:,.0f}")
with c3:
    st.metric("CA nouveau", f"{results['ca_nouveau']:,.0f}")

d1, d2 = st.columns(2)
with d1:
    st.metric("Marge base", f"{results['marge_base']:,.0f}")
with d2:
    st.metric("Marge additionnelle", f"{results['marge_incrementale']:,.0f}")
