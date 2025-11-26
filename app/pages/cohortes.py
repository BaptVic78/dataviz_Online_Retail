import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io

from utils import (
    compute_cohort_matrix,
    load_data,
    plot_retention_heatmap,
    densite,
    plot_retention_curves,
    plot_average_retention,
    add_download_button
)

# ------------------------------------------------
# CONFIG PAGE
# ------------------------------------------------
st.set_page_config(
    page_title="Rétentions par Cohortes",
    page_icon="📉",
    layout="wide",
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
    .kpi-label {
        font-size: 0.8rem;
        color: #cbd5e1;
        text-transform: uppercase;
        letter-spacing: .05em;
    }
    .kpi-value {
        font-size: 1.4rem;
        font-weight: 600;
        color: #f9fafb;
        margin-top: 0.2rem;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

def _kpi(label, value):
    return f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
    """

# ======================================================
# PAGE COHORTES
# ======================================================
def show_cohort_page():
    # ---------------------------
    # HEADER
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Cohortes</div>
                <div class="section-title">📉 Rétentions par Cohortes d'Acquisition</div>
            </div>
            <p style="color:#9ca3af;">
                Analyse de la rétention client dans le temps, par mois d’acquisition.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------
    # LOAD DATA
    # ---------------------------
    df = load_data()

    # Bulle Aperçu données + stats de base
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Données</div>
                <div class="section-title">🧾 Aperçu du dataset</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Voir un aperçu des données brutes (100 premières lignes)"):
        st.dataframe(df.head(100), use_container_width=True)

    # Quelques KPIs simples (si les colonnes existent)
    if "CustomerID" in df.columns and "InvoiceNo" in df.columns:
        n_clients = df["CustomerID"].nunique()
        n_orders = df["InvoiceNo"].nunique()
        if "TotalPrice" in df.columns:
            ca_total = df["TotalPrice"].sum()
        elif "Total" in df.columns:
            ca_total = df["Total"].sum()
        else:
            ca_total = np.nan

        c1, c2, c3 = st.columns(3)
        c1.markdown(_kpi("Clients uniques", f"{n_clients:,}"), unsafe_allow_html=True)
        c2.markdown(_kpi("Commandes uniques", f"{n_orders:,}"), unsafe_allow_html=True)
        if not np.isnan(ca_total):
            c3.markdown(_kpi("CA total (approx.)", f"{ca_total:,.0f} €"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # MATRICE DE RÉTENTION
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Rétention</div>
                <div class="section-title">🔥 Matrice de rétention par cohorte</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    cohort_matrix = compute_cohort_matrix(df)
    plot_retention_heatmap(cohort_matrix)

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # DENSITÉ / DISTRIBUTION
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Comportement</div>
                <div class="section-title">📊 Distribution & densité des retours clients</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    densite(df)

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # COURBES DE RÉTENTION
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Évolution</div>
                <div class="section-title">📉 Courbes de rétention par cohorte</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    plot_retention_curves(cohort_matrix)

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # RÉTENTION MOYENNE
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Synthèse</div>
                <div class="section-title">📐 Rétention moyenne toutes cohortes</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    plot_average_retention(cohort_matrix)

    st.markdown("</div>", unsafe_allow_html=True)


# Entrée
if __name__ == "__main__":
    show_cohort_page()
