import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

from utils import (
    load_data,
    compute_avg_purchase_frequency,
    compute_customer_lifespan,
    calculate_clv,
)

# ------------------------------------------------
#   CONFIG
# ------------------------------------------------
st.set_page_config(
    page_title="Dashboard Marketing",
    page_icon="📊",
    layout="wide",
)

# CSS
st.markdown(
    """
    <style>
    .kpi-card {
        background-color: #1f2933;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid #3b4252;
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
#   FONCTION PRINCIPALE
# ------------------------------------------------
def show_dashboard():

    st.title("📊 Tableau de Bord Marketing")

    # ---------------------------
    # 1. Chargement des données
    # ---------------------------
    df = load_data()

    if df.empty:
        st.error("Impossible de charger les données.")
        return

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Quarter"] = df["InvoiceDate"].dt.year.astype(str) + "Q" + df["InvoiceDate"].dt.quarter.astype(str)

    # ---------------------------
    # 2. Chargement RFM
    # ---------------------------
    rfm_path = "data/processed/df_rfm_resultat.csv"

    try:
        df_rfm = pd.read_csv(rfm_path)
    except FileNotFoundError:
        st.error(f"❌ Fichier RFM introuvable : {rfm_path}")
        return

    # ---------------------------
    # 3. RFM Label sans emoji
    # ---------------------------
    def label_rfm(score):
        if score >= 500:
            return "Champions"
        elif score >= 400:
            return "Fidèles"
        elif score >= 300:
            return "Potentiels"
        elif score >= 200:
            return "À Risque"
        else:
            return "Perdus"

    df_rfm["RFM_Label"] = df_rfm["RFM_Pourcentage"].apply(label_rfm)

    # ---------------------------
    # 4. Filtres
    # ---------------------------
    with st.sidebar:
        st.header("🎛 Filtres d'analyse")

        min_date = df["InvoiceDate"].min().date()
        max_date = df["InvoiceDate"].max().date()

        start_date, end_date = st.date_input(
            "Période",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        time_unit = st.radio("Unité de temps", ["Mois", "Trimestre"])

        countries = ["Tous"] + sorted(df["Country"].dropna().unique().tolist())
        country_choice = st.selectbox("Pays", countries)

        max_total = float(df["TotalPrice"].quantile(0.95))
        order_threshold = st.slider("Seuil minimum (€)", 0.0, max_total, 0.0)

        returns_mode = st.radio("Mode retours", ["Inclure", "Exclure", "Neutraliser"])

    # ---------------------------
    # 5. Application filtres
    # ---------------------------
    df_f = df[(df["InvoiceDate"].dt.date >= start_date) & (df["InvoiceDate"].dt.date <= end_date)].copy()

    if country_choice != "Tous":
        df_f = df_f[df_f["Country"] == country_choice]

    # Garder les retours même si TotalPrice < threshold
    df_f = df_f[(df_f["TotalPrice"] >= order_threshold) | (df_f["Quantity"] < 0)]

    if returns_mode == "Exclure":
        df_f = df_f[df_f["Quantity"] > 0]

    elif returns_mode == "Neutraliser":
        df_f.loc[df_f["Quantity"] < 0, "TotalPrice"] = 0

    # Debug retours
    n_before = (df["Quantity"] < 0).sum()
    n_after = (df_f["Quantity"] < 0).sum()

    with st.sidebar:
        st.subheader("🔍 Vérification retours")
        st.write(f"Retours avant filtres : **{n_before}**")
        st.write(f"Retours après filtres : **{n_after}**")

    # ---------------------------
    # Merge RFM
    # ---------------------------
    df_f_rfm = df_f.merge(
        df_rfm,
        how="left",
        left_on="CustomerID",
        right_on="Customer ID"
    )

    # ---------------------------
    # KPIs
    # ---------------------------
    st.markdown("### 📌 KPIs")

    total_revenue = df_f["TotalPrice"].sum()
    n_customers = df_f["CustomerID"].nunique()
    avg_order_value = total_revenue / len(df_f)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_kpi("Clients actifs", f"{n_customers:,}"), unsafe_allow_html=True)
    c2.markdown(_kpi("CA total", f"{total_revenue:,.0f} €"), unsafe_allow_html=True)
    c3.markdown(_kpi("Panier moyen", f"{avg_order_value:,.2f} €"), unsafe_allow_html=True)
    c4.markdown(_kpi("Transactions", f"{len(df_f):,}"), unsafe_allow_html=True)

    st.markdown("---")

    # ---------------------------
    # Graph CA temporel
    # ---------------------------
    st.subheader("📈 Tendances CA")

    time_col = "Month" if time_unit == "Mois" else "Quarter"
    rev_time = df_f.groupby(time_col)["TotalPrice"].sum().reset_index()

    fig = px.line(rev_time, x=time_col, y="TotalPrice", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------
    # RFM TABLE + LÉGENDE
    # ---------------------------
    st.subheader("🧩 Segments RFM")

    st.markdown("""
    **Champions (score 500+)**  
    Clients récents, très fréquents, gros paniers.

    **Fidèles (score 400–499)**  
    Achètent souvent, très bonne rétention.

    **Potentiels (score 300–399)**  
    Peu fréquents mais paniers intéressants → à activer davantage.

    **À Risque (score 200–299)**  
    N'ont pas acheté depuis longtemps → priorité de relance.

    **Perdus (score < 200)**  
    Clients inactifs → faible probabilité de retour.
    """)

    rfm_display = df_rfm[
        ["Customer ID", "Monetaire_Total_Depense",
         "Frequence_Nb_Commandes", "RFM_Pourcentage", "RFM_Label"]
    ]

    st.dataframe(rfm_display, use_container_width=True)

    # ---------------------------
    # TOP PRODUITS
    # ---------------------------
    st.subheader("🏆 Top Produits")

    top_sales = (
        df_f.groupby("Description")["Quantity"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    top_returns = (
        df_f[df_f["Quantity"] < 0]
        .groupby("Description")["Quantity"]
        .sum()
        .sort_values()
        .head(10)
    )

    c1, c2 = st.columns(2)
    c1.write("### Produits les plus vendus")
    c1.dataframe(top_sales)

    c2.write("### Produits les plus retournés")
    c2.dataframe(top_returns)


# ------------------------------------------------
if __name__ == "__main__":
    show_dashboard()
