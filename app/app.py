import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
from datetime import datetime

from utils import (
    load_data,
    compute_avg_purchase_frequency,
    compute_customer_lifespan,
    calculate_clv,
)

# ------------------------------------------------
#                 CONFIG
# ------------------------------------------------
st.set_page_config(
    page_title="Dashboard Marketing",
    page_icon="📊",
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

    /* --- Titres "en bulles" --- */
    .section-bubble {
        background-color: #020617;
        border-radius: 14px;
        border: 1px solid #1f2937;
        padding: 1.2rem 1.4rem 1.4rem 1.4rem;
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
        font-size: 1.1rem;
        font-weight: 600;
        color: #f9fafb;
    }

    /* KPI cards */
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

    /* Badges filtres */
    .filter-badge {
        background: #2563eb;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        margin-right: 6px;
    }

    /* Cartes navigation */
    .nav-card {
        background-color: #020617;
        border-radius: 12px;
        border: 1px solid #1f2937;
        padding: 1rem 1.2rem;
        height: 100%;
    }
    .nav-card h3 {
        margin-bottom: 0.3rem;
    }
    .nav-card p {
        font-size: 0.9rem;
        color: #e5e7eb;
        margin-bottom: 0.6rem;
    }

    /* Tooltip */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: pointer;
        color: #60a5fa;
        font-weight: bold;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 260px;
        background-color: #111827;
        color: #f9fafb;
        text-align: left;
        border-radius: 6px;
        padding: 10px;
        border: 1px solid #374151;
        font-size: 0.75rem;
        position: absolute;
        z-index: 10;
        bottom: 125%; 
        left: 50%; 
        margin-left: -130px;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
    }

    /* On masque le menu/ footer pour un rendu plus "produit" */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .section-bubble {
    background: #0d1117;
    border: 1px solid #1f2937;
    padding: 5px 26px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 25px;
    margin-bottom: 15px;
}

/* Badge bleu */
.section-tag {
    background: linear-gradient(145deg, #2563eb, #1e40af);
    padding: 6px 14px;
    border-radius: 6px;
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: .04em;
}

/* 🆕 TITRE PLUS GRAND ET PLUS LARGE */
.section-title {
    font-size: 2rem !important;   /* avant c’était 1rem */
    font-weight: 700 !important;
    color: #e5e7eb !important;
    margin: 0;
    padding: 0;
}


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

# ------------------------------------------------
#      TOOLTIP (infobulles ℹ️)
# ------------------------------------------------
def tooltip(label, text):
    return f"""
    <span class='tooltip'>{label} ℹ️
        <span class='tooltiptext'>{text}</span>
    </span>
    """

# ------------------------------------------------
#      CLV SAFE
# ------------------------------------------------
def compute_clv_safe(aov, freq, lifespan):
    try:
        return calculate_clv(aov, freq, lifespan)
    except Exception:
        return aov * freq * lifespan

# ------------------------------------------------
# EXPORT CSV
# ------------------------------------------------
def export_filtered_csv(df_filtered):
    csv_buffer = io.StringIO()
    df_filtered.to_csv(csv_buffer, index=False, sep=";")
    st.download_button(
        label="📥 Export CSV (filtré)",
        data=csv_buffer.getvalue(),
        file_name=f"online_retail_export_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )

# ------------------------------------------------
# EXPORT PNG
# ------------------------------------------------
def export_png_plot(fig, title="graphique"):
    try:
        buf = io.BytesIO()
        fig.write_image(buf, format="png", scale=2)
        st.download_button(
            label="🖼️ Export PNG du CA",
            data=buf.getvalue(),
            file_name=f"{title}_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}.png",
            mime="image/png"
        )
    except Exception:
        st.download_button(
            label="💾 Export HTML (PNG indisponible)",
            data=fig.to_html().encode(),
            file_name=f"{title}.html",
            mime="text/html"
        )

# ------------------------------------------------
#             DASHBOARD PRINCIPAL
# ------------------------------------------------
def show_dashboard():

    st.markdown(
        "<h1 style='margin-bottom:0.2rem;'>📊 Tableau de Bord Marketing</h1>"
        "<p style='color:#9ca3af;margin-bottom:1.2rem;'>"
        "Suivi global des performances e-commerce, segments RFM et indicateurs de rétention."
        "</p>",
        unsafe_allow_html=True,
    )

    df = load_data()
    if df.empty:
        st.error("Impossible de charger les données.")
        return

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Quarter"] = df["InvoiceDate"].dt.to_period("Q").astype(str)

    # ---------------------------
    # Load RFM
    # ---------------------------
    df_rfm = pd.read_csv("data/processed/df_rfm_resultat.csv")

    def label_rfm(percent):
        if percent >= 400: return "Champions"
        elif percent >= 300: return "Fidèles"
        elif percent >= 200: return "Potentiels"
        elif percent >= 120: return "À Risque"
        elif percent >= 100: return "Perdus"
        else: return "Perdus"

    df_rfm["RFM_Label"] = df_rfm["RFM_Pourcentage"].apply(label_rfm)

    # ---------------------------
    # Filtres (sidebar)
    # ---------------------------
    with st.sidebar:
        st.header("🎛 Filtres")

        min_date = df["InvoiceDate"].min().date()
        max_date = df["InvoiceDate"].max().date()

        start_date, end_date = st.date_input("Période", value=(min_date, max_date))
        time_unit = st.radio("Unité", ["Mois", "Trimestre"])
        country_choice = st.selectbox("Pays", ["Tous"] + sorted(df["Country"].dropna().unique()))
        threshold = st.slider("Seuil minimum (€)", 0.0, float(df["TotalPrice"].quantile(0.95)), 0.0)
        returns_mode = st.radio("Retours", ["Inclure", "Exclure", "Neutraliser"])

    # ---------------------------
    # Application des filtres
    # ---------------------------
    df_f = df[(df["InvoiceDate"].dt.date >= start_date) &
              (df["InvoiceDate"].dt.date <= end_date)].copy()

    if country_choice != "Tous":
        df_f = df_f[df_f["Country"] == country_choice]

    df_f = df_f[(df_f["TotalPrice"] >= threshold) | (df_f["Quantity"] < 0)]

    if returns_mode == "Exclure":
        df_f = df_f[df_f["Quantity"] > 0]
        st.markdown("<span class='filter-badge'>Retours exclus</span>", unsafe_allow_html=True)

    if returns_mode == "Neutraliser":
        df_f.loc[df_f["Quantity"] < 0, "TotalPrice"] = 0

    # ---------------------------
    # KPIs PRINCIPAUX (bulle)
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Vue globale</div>
                <div class="section-title">📌 KPIs principaux</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    total_revenue = df_f["TotalPrice"].sum()
    n_customers = df_f["CustomerID"].nunique()
    avg_order_value = total_revenue / max(len(df_f), 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_kpi("Clients actifs", f"{n_customers:,}"), unsafe_allow_html=True)
    c2.markdown(_kpi("CA total", f"{total_revenue:,.0f} €"), unsafe_allow_html=True)
    c3.markdown(_kpi("Panier moyen", f"{avg_order_value:,.2f} €"), unsafe_allow_html=True)
    c4.markdown(_kpi("Transactions", f"{len(df_f):,}"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # fin bulle KPIs principaux

    # ---------------------------
    # KPIs OVERVIEW (bulle)
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Rétention & valeur client</div>
                <div class="section-title">🌟 KPIs – Overview</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    rev_acquisition = df[df['CohortIndex'] == 0]['TotalPrice'].sum()
    rev_retention = df[df['CohortIndex'] > 0]['TotalPrice'].sum()
    share_retention = (rev_retention / total_revenue) * 100 if total_revenue > 0 else 0
    avg_freq = compute_avg_purchase_frequency(df_f)
    avg_lifespan = compute_customer_lifespan(df_f)
    clv_baseline = compute_clv_safe(avg_order_value, avg_freq, avg_lifespan)
    north_star = df_f.groupby("Month")["InvoiceNo"].nunique().mean()

    t_seg = "Nombre de segments RFM basé sur RFM_Pourcentage."
    t_clv = (
    "CLV = valeur totale qu’un client rapporte sur sa durée de vie.\n"
    "Formule : Panier moyen × Fréquence × Durée de vie.\n"
    f"Calcul : {avg_order_value:,.0f}€ × {avg_freq:.2f} × {avg_lifespan:.1f}."
)
    t_ns = "Nombre moyen de commandes mensuelles uniques."

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    help_active = "Nombre de clients uniques ayant passé au moins une commande sur la période sélectionnée."
    c1.markdown(_kpi(tooltip("Clients actifs", help_active), f"{n_customers:,}"), unsafe_allow_html=True)
    help_acq = "Revenu généré par les nouveaux clients (Mois 0) sur la période."
    c2.markdown(_kpi(tooltip("CA Acquisition", help_acq), f"{rev_acquisition:,.0f} €"), unsafe_allow_html=True)
    help_ret = f"Revenu des clients historiques (Mois > 0). Représente {share_retention:.1f}% du CA total."
    c3.markdown(_kpi(tooltip("CA Rétention", help_ret), f"{rev_retention:,.0f} €"), unsafe_allow_html=True)
    c4.markdown(_kpi(tooltip("Segments RFM", t_seg), df_rfm["RFM_Label"].nunique()), unsafe_allow_html=True)
    c5.markdown(_kpi(tooltip("CLV baseline", t_clv), f"{clv_baseline:,.0f} €"), unsafe_allow_html=True)
    c6.markdown(_kpi(tooltip("North Star", t_ns), f"{north_star:,.0f}"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # fin bulle KPIs overview

    # ---------------------------
    # TENDANCE CA (bulle)
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Performance</div>
                <div class="section-title">📈 Tendances du chiffre d’affaires</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    time_col = "Month" if time_unit == "Mois" else "Quarter"
    rev_time = df_f.groupby(time_col)["TotalPrice"].sum().reset_index()

    fig = px.line(rev_time, x=time_col, y="TotalPrice", markers=True)
    fig.update_traces(text=rev_time["TotalPrice"].round(0), textposition="top center")

    st.plotly_chart(fig, use_container_width=True)
    export_png_plot(fig, title="tendance_CA")

    st.markdown("</div>", unsafe_allow_html=True)  # fin bulle tendance CA

    # ---------------------------
    # SEGMENTS RFM (bulle)
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Segmentation</div>
                <div class="section-title">🧩 Segments RFM</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    rfm_display = df_rfm[
        [
            "Customer ID",
            "Monetaire_Total_Depense",
            "Frequence_Nb_Commandes",
            "R_Score", "F_Score", "M_Score",
            "RFM_Somme", "RFM_Pourcentage",
            "RFM_Label"
        ]
    ]

    st.dataframe(rfm_display, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)  # fin bulle RFM

    # ---------------------------
    # TOP PRODUITS (bulle)
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Catalogue</div>
                <div class="section-title">🏆 Top produits</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    top_sales = df_f.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(10)
    top_returns = df_f[df_f["Quantity"] < 0].groupby("Description")["Quantity"].sum().sort_values().head(10)

    c1, c2 = st.columns(2)
    c1.write("### Produits les plus vendus")
    c1.dataframe(top_sales)

    c2.write("### Produits les plus retournés")
    c2.dataframe(top_returns)

    st.markdown("</div>", unsafe_allow_html=True)  # fin bulle top produits

    # ---------------------------
    # EXPORT CSV (bulle)
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Données</div>
                <div class="section-title">📤 Export des données filtrées</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    export_filtered_csv(df_f)

    st.markdown("</div>", unsafe_allow_html=True)  # fin bulle export

    # ---------------------------
    # NAVIGATION (bulle)
    # ---------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Navigation</div>
                <div class="section-title">Où voulez-vous aller ?</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("<div class='nav-card'>", unsafe_allow_html=True)
        st.markdown("### 📉 Diagnostic")
        st.write("Analysez la rétention et le comportement par cohorte.")
        st.page_link("pages/cohortes.py", label="Voir les Cohortes", icon="📊", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='nav-card'>", unsafe_allow_html=True)
        st.markdown("### 🎯 Segmentation")
        st.write("Priorisez vos actions grâce à l'analyse RFM.")
        st.page_link("pages/segments.py", label="Voir les Segments RFM", icon="👥", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='nav-card'>", unsafe_allow_html=True)
        st.markdown("### 🔮 Prédictions")
        st.write("Simulez vos scénarios de croissance (CLV).")
        st.page_link("pages/scenarios.py", label="Voir le Simulateur", icon="🚀", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # fin bulle navigation


# ------------------------------------------------
# RUN APP
# ------------------------------------------------
if __name__ == "__main__":
    show_dashboard()
