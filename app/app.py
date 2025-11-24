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

# CSS général
st.markdown(
    """
    <style>
    .kpi-card {
        background-color: #1f2933;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid #3b4252;
        text-align:center;
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
    .filter-badge {
        background: #2563eb;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        margin-right: 6px;
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
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

def tooltip(label, text):
    return f"""
    <span class='tooltip'>{label} ℹ️
        <span class='tooltiptext'>{text}</span>
    </span>
    """

# ------------------------------------------------
#      CLV SAFE (corrige l'erreur TypeError)
# ------------------------------------------------
def compute_clv_safe(aov, freq, lifespan):
    try:
        return calculate_clv(aov, freq, lifespan)
    except Exception:
        return aov * freq * lifespan

# ------------------------------------------------
#               EXPORT CSV
# ------------------------------------------------
def export_filtered_csv(df_filtered):
    csv_buffer = io.StringIO()
    df_filtered.to_csv(csv_buffer, index=False, sep=";")
    csv_data = csv_buffer.getvalue()

    fname = f"online_retail_export_{datetime.now().strftime('%Y-%m-%d')}.csv"

    st.download_button(
        label="📥 Export CSV (filtré)",
        data=csv_data,
        file_name=fname,
        mime="text/csv"
    )

# ------------------------------------------------
#               EXPORT PNG (fallback sans Kaleido)
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
        html_bytes = fig.to_html(include_plotlyjs="cdn").encode()
        st.download_button(
            label="💾 Export HTML du graphique (PNG indisponible)",
            data=html_bytes,
            file_name=f"{title}.html",
            mime="text/html"
        )

# ------------------------------------------------
#             DASHBOARD PRINCIPAL
# ------------------------------------------------
def show_dashboard():

    st.title("📊 Tableau de Bord Marketing")

    # ---------------------------
    # 1. Load data
    # ---------------------------
    df = load_data()

    if df.empty:
        st.error("Impossible de charger les données.")
        return

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Quarter"] = df["InvoiceDate"].dt.to_period("Q").astype(str)

    # ---------------------------
    # 2. Load RFM (TON FICHIER)
    # ---------------------------
    df_rfm = pd.read_csv("data/processed/df_rfm_resultat.csv")

    # ---------------------------
    # Segmentation RFM via RFM_POURCENTAGE (TA DEMANDE)
    # ---------------------------
    def label_rfm(percent):
        if percent >= 400:
            return "Champions"
        elif percent >= 300:
            return "Fidèles"
        elif percent >= 200:
            return "Potentiels"
        elif percent >= 120:
            return "À Risque"
        elif percent >= 100:
            return "Perdus"
        else:
            return "Perdus"

    df_rfm["RFM_Label"] = df_rfm["RFM_Pourcentage"].apply(label_rfm)

    # ---------------------------
    # 3. Filtres
    # ---------------------------
    with st.sidebar:
        st.header("🎛 Filtres")

        min_date = df["InvoiceDate"].min().date()
        max_date = df["InvoiceDate"].max().date()

        start_date, end_date = st.date_input("Période", value=(min_date, max_date))

        time_unit = st.radio("Unité", ["Mois", "Trimestre"])

        country_choice = st.selectbox(
            "Pays",
            ["Tous"] + sorted(df["Country"].dropna().unique())
        )

        threshold = st.slider(
            "Seuil minimum (€)",
            0.0,
            float(df["TotalPrice"].quantile(0.95)),
            0.0
        )

        returns_mode = st.radio("Retours", ["Inclure", "Exclure", "Neutraliser"])

    # ---------------------------
    # 4. Application des filtres
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
    # 5. KPIs PRINCIPAUX
    # ---------------------------
    st.markdown("## 📌 KPIs Principaux")

    total_revenue = df_f["TotalPrice"].sum()
    n_customers = df_f["CustomerID"].nunique()
    avg_order_value = total_revenue / max(len(df_f),1)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_kpi("Clients actifs", f"{n_customers:,}"), unsafe_allow_html=True)
    c2.markdown(_kpi("CA total", f"{total_revenue:,.0f} €"), unsafe_allow_html=True)
    c3.markdown(_kpi("Panier moyen", f"{avg_order_value:,.2f} €"), unsafe_allow_html=True)
    c4.markdown(_kpi("Transactions", f"{len(df_f):,}"), unsafe_allow_html=True)

    st.markdown("---")

    # ---------------------------
    # 6. KPIs OVERVIEW (ℹ️)
    # ---------------------------
    st.markdown("## 🌟 KPIs – Overview")

    df_f["FirstPurchase"] = df_f.groupby("CustomerID")["InvoiceDate"].transform("min")
    df_f["CohortAge"] = ((df_f["InvoiceDate"] - df_f["FirstPurchase"]).dt.days // 30)

    ca_age_cohorte = df_f.groupby("CohortAge")["TotalPrice"].sum().mean()

    avg_freq = compute_avg_purchase_frequency(df_f)
    avg_lifespan = compute_customer_lifespan(df_f)

    clv_baseline = compute_clv_safe(avg_order_value, avg_freq, avg_lifespan)

    north_star = df_f.groupby("Month")["InvoiceNo"].nunique().mean()

    # Infobulles (définitions + exemples)
    t_ca = "CA moyen généré en fonction de l’ancienneté."
    t_seg = "Nombre de segments RFM basé sur RFM_Pourcentage."
    t_clv = f"CLV = {avg_order_value:,.0f}€ × {avg_freq:.2f} × {avg_lifespan:.1f}."
    t_ns = "Nombre moyen de commandes mensuelles uniques."

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(_kpi("Clients actifs", f"{n_customers:,}"), unsafe_allow_html=True)
    c2.markdown(_kpi(tooltip("CA / cohorte", t_ca), f"{ca_age_cohorte:,.0f} €"), unsafe_allow_html=True)
    c3.markdown(_kpi(tooltip("Segments RFM", t_seg), df_rfm["RFM_Label"].nunique()), unsafe_allow_html=True)
    c4.markdown(_kpi(tooltip("CLV baseline", t_clv), f"{clv_baseline:,.0f} €"), unsafe_allow_html=True)
    c5.markdown(_kpi(tooltip("North Star", t_ns), f"{north_star:,.0f}"), unsafe_allow_html=True)

    st.markdown("---")

    # ---------------------------
    # 7. TENDANCE CA
    # ---------------------------
    st.subheader("📈 Tendances du CA")

    time_col = "Month" if time_unit == "Mois" else "Quarter"
    rev_time = df_f.groupby(time_col)["TotalPrice"].sum().reset_index()

    fig = px.line(rev_time, x=time_col, y="TotalPrice", markers=True)
    fig.update_traces(text=rev_time["TotalPrice"].round(0), textposition="top center")

    st.plotly_chart(fig, use_container_width=True)
    export_png_plot(fig, title="tendance_CA")

    # ---------------------------
    # 8. SEGMENTS RFM (Basé sur RFM_POURCENTAGE)
    # ---------------------------
    st.subheader("🧩 Segments RFM")

    rfm_display = df_rfm[
        ["Customer ID",
         "Monetaire_Total_Depense",
         "Frequence_Nb_Commandes",
         "R_Score", "F_Score", "M_Score",
         "RFM_Somme", "RFM_Pourcentage",
         "RFM_Label"]
    ]

    st.dataframe(rfm_display, use_container_width=True)

    # ---------------------------
    # 9. TOP PRODUITS
    # ---------------------------
    st.subheader("🏆 Top Produits")

    top_sales = df_f.groupby("Description")["Quantity"].sum().sort_values(ascending=False).head(10)
    top_returns = df_f[df_f["Quantity"] < 0].groupby("Description")["Quantity"].sum().sort_values().head(10)

    c1, c2 = st.columns(2)
    c1.write("### Produits les plus vendus")
    c1.dataframe(top_sales)

    c2.write("### Produits les plus retournés")
    c2.dataframe(top_returns)

    # ---------------------------
    # 10. EXPORT CSV
    # ---------------------------
    st.subheader("📤 Export des données filtrées")
    export_filtered_csv(df_f)


# ------------------------------------------------
#               RUN APP
# ------------------------------------------------
if __name__ == "__main__":
    show_dashboard()
