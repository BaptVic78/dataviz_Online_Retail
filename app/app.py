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

    .filter-badge {
        background: #2563eb;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        margin-right: 6px;
    }

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

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------
# Fonctions utilitaires
# ------------------------------------------------

def _kpi(label, value):
    return f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
    """

def tooltip(label, text):
    return f"""
    <span class='tooltip'>{label} ℹ️
        <span class='tooltiptext'>{text}</span>
    </span>
    """

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
            label="🖼️ Export PNG",
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
# MAIN DASHBOARD
# ------------------------------------------------

def show_dashboard():

    st.markdown(
        "<h1>📊 Tableau de Bord Marketing</h1>"
        "<p style='color:#9ca3af;'>Suivi global des performances e-commerce, RFM et rétention.</p>",
        unsafe_allow_html=True,
    )

    df = load_data()
    if df.empty:
        st.error("Impossible de charger les données.")
        return

    # Dates
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Quarter"] = df["InvoiceDate"].dt.to_period("Q").astype(str)

    # Chargement RFM
    df_rfm = pd.read_csv("data/processed/df_rfm_resultat.csv")

    def label_rfm(percent):
        if percent >= 400: return "Champions"
        elif percent >= 300: return "Fidèles"
        elif percent >= 200: return "Potentiels"
        elif percent >= 120: return "À Risque"
        elif percent >= 100: return "Perdus"
        else: return "Perdus"

    df_rfm["RFM_Label"] = df_rfm["RFM_Pourcentage"].apply(label_rfm)

    # ------------------------------------------------
    # 🎛 SIDEBAR — Tous les filtres
    # ------------------------------------------------
    with st.sidebar:
        st.header("🎛 Filtres")

        min_date = df["InvoiceDate"].min().date()
        max_date = df["InvoiceDate"].max().date()

        start_date, end_date = st.date_input("Période", value=(min_date, max_date))
        time_unit = st.radio("Unité", ["Mois", "Trimestre"])
        country_choice = st.selectbox("Pays", ["Tous"] + sorted(df["Country"].dropna().unique()))
        threshold = st.slider("Seuil minimum (€)", 0.0, float(df["TotalPrice"].quantile(0.95)), 0.0)
        returns_mode = st.radio("Retours", ["Inclure", "Exclure", "Neutraliser"])

        # ⭐ FILTRE RFM
        rfm_types = ["Tous"] + sorted(df_rfm["RFM_Label"].unique())
        rfm_choice = st.selectbox("Type de client (RFM)", rfm_types)

    # ------------------------------------------------
    # Application des filtres
    # ------------------------------------------------
    df_f = df[
        (df["InvoiceDate"].dt.date >= start_date) &
        (df["InvoiceDate"].dt.date <= end_date)
    ].copy()

    if country_choice != "Tous":
        df_f = df_f[df_f["Country"] == country_choice]

    df_f = df_f[(df_f["TotalPrice"] >= threshold) | (df_f["Quantity"] < 0)]

    if returns_mode == "Exclure":
        df_f = df_f[df_f["Quantity"] > 0]
        st.markdown("<span class='filter-badge'>Retours exclus</span>", unsafe_allow_html=True)

    if returns_mode == "Neutraliser":
        df_f.loc[df_f["Quantity"] < 0, "TotalPrice"] = 0

    # ⭐ Filtre RFM
    if rfm_choice != "Tous":
        selected_ids = df_rfm[df_rfm["RFM_Label"] == rfm_choice]["Customer ID"].unique()
        df_f = df_f[df_f["CustomerID"].isin(selected_ids)]
        st.markdown(f"<span class='filter-badge'>Segment client : {rfm_choice}</span>", unsafe_allow_html=True)

    # ------------------------------------------------
    # KPIs PRINCIPAUX (TOP)
    # ------------------------------------------------
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
    n_tx = len(df_f)
    avg_order_value = total_revenue / max(n_tx, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_kpi("Clients actifs", f"{n_customers:,}"), unsafe_allow_html=True)
    c2.markdown(_kpi("CA total", f"{total_revenue:,.0f} €"), unsafe_allow_html=True)
    c3.markdown(_kpi("Panier moyen", f"{avg_order_value:,.2f} €"), unsafe_allow_html=True)
    c4.markdown(_kpi("Transactions", f"{n_tx:,}"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    # ------------------------------------------------
    # KPIs RÉTENTION & CLV
    # ------------------------------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Rétention & Valeur client</div>
                <div class="section-title">🌟 KPIs – Rétention & CLV</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Recalcul propre des métriques
    rev_acquisition = df[df["CohortIndex"] == 0]["TotalPrice"].sum()
    rev_retention = df[df["CohortIndex"] > 0]["TotalPrice"].sum()
    share_retention = (rev_retention / total_revenue) * 100 if total_revenue > 0 else 0

    avg_freq = compute_avg_purchase_frequency(df_f)
    avg_lifespan = compute_customer_lifespan(df_f)
    clv_baseline = compute_clv_safe(avg_order_value, avg_freq, avg_lifespan)
    north_star = df_f.groupby("Month")["InvoiceNo"].nunique().mean()

    t_seg = "Nombre de segments RFM identifiés."
    t_clv = (
        "CLV = Panier moyen × Fréquence × Durée de vie.\n"
        f"Calcul = {avg_order_value:,.0f}€ × {avg_freq:.2f} × {avg_lifespan:.1f}"
    )
    t_ns = "Nombre moyen de commandes uniques par mois."

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.markdown(_kpi(tooltip("Clients actifs", "Clients avec ≥ 1 achat"), f"{n_customers:,}"),
                  unsafe_allow_html=True)

    col2.markdown(_kpi(tooltip("CA Acquisition", "Clients nouveaux – Cohorte 0"),
                       f"{rev_acquisition:,.0f} €"), unsafe_allow_html=True)

    col3.markdown(_kpi(tooltip("CA Rétention", f"{share_retention:.1f}% du CA total"),
                       f"{rev_retention:,.0f} €"), unsafe_allow_html=True)

    col4.markdown(_kpi(tooltip("Segments RFM", t_seg),
                       df_rfm["RFM_Label"].nunique()), unsafe_allow_html=True)

    col5.markdown(_kpi(tooltip("CLV Baseline", t_clv),
                       f"{clv_baseline:,.0f} €"), unsafe_allow_html=True)

    col6.markdown(_kpi(tooltip("North Star", t_ns),
                       f"{north_star:,.0f}"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------
    # TENDANCE DU CA
    # ------------------------------------------------
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
    fig.update_traces(text=rev_time["TotalPrice"].round(0))

    st.plotly_chart(fig, use_container_width=True)
    export_png_plot(fig, title="tendance_CA")

    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------
    # TABLEAU RFM
    # ------------------------------------------------
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
            "Customer ID", "Monetaire_Total_Depense", "Frequence_Nb_Commandes",
            "R_Score", "F_Score", "M_Score", "RFM_Somme",
            "RFM_Pourcentage", "RFM_Label"
        ]
    ]

    st.dataframe(rfm_display, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------
    # TOP PRODUITS
    # ------------------------------------------------
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

    col1, col2 = st.columns(2)
    col1.write("### Produits les plus vendus")
    col1.dataframe(top_sales)
    col2.write("### Produits les plus retournés")
    col2.dataframe(top_returns)

    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------
    # EXPORT CSV
    # ------------------------------------------------
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
    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------
    # NAVIGATION EN BAS
    # ------------------------------------------------
    st.markdown(
        """
        <div class="section-bubble">
            <div class="section-header">
                <div class="section-pill">Navigation</div>
                <div class="section-title">🧭 Où voulez-vous aller ?</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    nav1, nav2, nav3 = st.columns(3)

    with nav1:
        st.markdown("<div class='nav-card'>", unsafe_allow_html=True)
        st.markdown("### 📉 Diagnostic")
        st.write("Analysez la rétention et les cohortes.")
        st.page_link("pages/cohortes.py", label="Voir les Cohortes", icon="📊")
        st.markdown("</div>", unsafe_allow_html=True)

    with nav2:
        st.markdown("<div class='nav-card'>", unsafe_allow_html=True)
        st.markdown("### 🎯 Segmentation")
        st.write("Analyse RFM complète.")
        st.page_link("pages/segments.py", label="Segments RFM", icon="👥")
        st.markdown("</div>", unsafe_allow_html=True)

    with nav3:
        st.markdown("<div class='nav-card'>", unsafe_allow_html=True)
        st.markdown("### 🔮 Prédictions")
        st.write("Simulateur CLV.")
        st.page_link("pages/scenarios.py", label="Simulateur CLV", icon="🚀")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # Fin navigation


# ------------------------------------------------
# RUN APP
# ------------------------------------------------
if __name__ == "__main__":
    show_dashboard()
