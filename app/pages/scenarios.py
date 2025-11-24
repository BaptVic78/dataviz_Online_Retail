import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ======================
# 1. Charger le fichier CSV
# ======================
@st.cache_data
def load_rfm():
    df = pd.read_csv("data/processed/df_rfm_resultat.csv")
    df["Date_Premier_Achat"] = pd.to_datetime(df["Date_Premier_Achat"])
    return df


# ======================
# 2. Fonction de labeling RFM
# ======================
def label_rfm(percent):
    if percent >= 400: return "Champions"
    elif percent >= 300: return "Fidèles"
    elif percent >= 200: return "Potentiels"
    elif percent >= 120: return "À Risque"
    elif percent >= 100: return "Perdus"
    else: return "Perdus"


# ======================
# 3. CLV empirique
# ======================
def calculate_clv_empirique(aov, freq, lifespan):
    return aov * freq * lifespan


# ======================
# 4. Durée de vie client (en années)
# ======================
def compute_lifespan(df):
    # ancienneté des clients : aujourd’hui - première date
    lifespan_days = (pd.Timestamp.today() - df["Date_Premier_Achat"]).dt.days
    return (lifespan_days / 365).mean()


# ======================
# PAGE STREAMLIT
# ======================
def show_scenarios():

    st.title("📈 Simulation d'Impact Marketing (CLV)")
    st.markdown("Analyse l'effet d'une remise, du taux de marge ou de la rétention sur la CLV.")

    df = load_rfm()
    df["Segment_RFM"] = df["RFM_Pourcentage"].apply(label_rfm)

    # ============================
    # 🧮 MÉTRIQUES DE BASE
    # ============================
    aov = df["Monetaire_Total_Depense"].mean()
    freq = df["Frequence_Nb_Commandes"].mean()
    lifespan = compute_lifespan(df)

    clv_baseline = calculate_clv_empirique(aov, freq, lifespan)

    # ============================
    # 🎛 SIDEBAR
    # ============================
    with st.sidebar:

        st.header("Paramètres du scénario")

        marge = st.slider("Marge brute (%)", 0.0, 100.0, 30.0)
        remise = st.slider("Remise (%)", 0.0, 80.0, 10.0)
        retention = st.slider("Taux de rétention (%)", 0.0, 100.0, 70.0)
        discount = st.slider("Taux d'actualisation (%)", 0.0, 30.0, 10.0)

        st.subheader("Segments RFM ciblés :")
        segments_selected = st.multiselect(
            "Choisir segments",
            df["Segment_RFM"].unique(),
            default=df["Segment_RFM"].unique().tolist()
        )

        df_filtered = df[df["Segment_RFM"].isin(segments_selected)]

    # recalcul si filtrage
    if len(df_filtered) == 0:
        st.error("Aucun client dans cette sélection.")
        return

    aov_new = df_filtered["Monetaire_Total_Depense"].mean() * (1 - remise / 100)
    freq_new = df_filtered["Frequence_Nb_Commandes"].mean()
    lifespan_new = lifespan * (retention / 100)

    clv_scenario = calculate_clv_empirique(aov_new, freq_new, lifespan_new)

    # ============================
    # 🎯 KPI
    # ============================
    col1, col2, col3 = st.columns(3)

    col1.metric("CLV Baseline", f"{clv_baseline:,.2f} €")
    col2.metric("CLV Scénario", f"{clv_scenario:,.2f} €",
                delta=f"{clv_scenario - clv_baseline:,.2f} €")

    impact_pct = ((clv_scenario - clv_baseline) / clv_baseline) * 100
    col3.metric("Impact (%)", f"{impact_pct:+.2f}%")

    # ============================
    # 📊 GRAPHIQUE
    # ============================
    st.subheader("📈 Sensibilité de la CLV au taux de rétention")

    retention_range = np.linspace(0.1, 0.99, 12)
    clv_sensitivity = [
        calculate_clv_empirique(aov_new, freq_new, lifespan * r)
        for r in retention_range
    ]

    fig = px.line(
        x=retention_range * 100,
        y=clv_sensitivity,
        labels={"x": "Rétention (%)", "y": "CLV (€)"},
        markers=True
    )

    fig.add_hline(
        y=clv_baseline,
        line_dash="dash",
        line_color="red",
        annotation_text=f"CLV baseline : {clv_baseline:,.2f} €"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ============================
    # 📘 RÉCAP
    # ============================
    st.subheader("🧾 Récapitulatif")

    recap = pd.DataFrame({
        "Paramètre": ["Marge", "Remise", "Rétention", "Taux d'actualisation"],
        "Valeur": [f"{marge}%", f"{remise}%", f"{retention}%", f"{discount}%"]
    })

    st.table(recap)


# afficher la page
show_scenarios()
