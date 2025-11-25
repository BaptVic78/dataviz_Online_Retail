import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ======================================================
# 1) Chargement des données RFM
# ======================================================
@st.cache_data
def load_rfm():
    df = pd.read_csv("data/processed/df_rfm_resultat.csv")
    df["Date_Premier_Achat"] = pd.to_datetime(df["Date_Premier_Achat"])
    return df

# ======================================================
# 2) Segmentation RFM
# ======================================================
def label_rfm(percent):
    if percent >= 400: return "Champions"
    elif percent >= 300: return "Fidèles"
    elif percent >= 200: return "Potentiels"
    elif percent >= 120: return "À Risque"
    elif percent >= 100: return "Perdus"
    else: return "Perdus"

# ======================================================
# 3) CLV = AOV × fréquence × ancienneté
# ======================================================
def calculate_clv(aov, freq, lifespan_years):
    return aov * freq * lifespan_years

def compute_lifespan_years(df):
    """Ancienneté = aujourd’hui - première commande"""
    lifespan_days = (pd.Timestamp.today() - df["Date_Premier_Achat"]).dt.days
    return (lifespan_days / 365).mean()

# ======================================================
# PAGE STREAMLIT
# ======================================================
def show_scenarios():

    st.title("📈 Simulation d'Impact Marketing (CLV)")
    st.markdown("Analyse l'effet d'une remise, de la marge et de la rétention sur la CLV.")

    # ---------------------------
    # Charger les données
    # ---------------------------
    df = load_rfm()
    df["Segment_RFM"] = df["RFM_Pourcentage"].apply(label_rfm)

    # ---------------------------
    # METRIQUES DE BASE
    # ---------------------------
    aov = df["Monetaire_Total_Depense"].mean()
    freq = df["Frequence_Nb_Commandes"].mean()
    lifespan = compute_lifespan_years(df)

    clv_baseline = calculate_clv(aov, freq, lifespan)

    # ---------------------------
    # SIDEBAR (paramètres)
    # ---------------------------
    with st.sidebar:
        st.header("⚙️ Paramètres du scénario")

        marge = st.slider("Marge brute (%)", 0.0, 100.0, 30.0)
        remise = st.slider("Remise (%)", 0.0, 80.0, 10.0)
        retention = st.slider("Taux de rétention (%)", 0.0, 100.0, 70.0)
        taux_actualisation = st.slider("Taux d'actualisation (%)", 0.0, 30.0, 10.0)

        st.subheader("🎯 Segments RFM ciblés")
        segments_selected = st.multiselect(
            "Choisir segments",
            df["Segment_RFM"].unique(),
            default=df["Segment_RFM"].unique().tolist()
        )

        st.subheader("🎬 Scénarios prédéfinis")
        if st.button("🚀 Croissance"):
            remise = 5
            retention = 90
            marge = 25

        if st.button("💰 Optimisation Marges"):
            remise = 0
            marge = 40
            retention = 70

        if st.button("🎯 Fidélisation"):
            remise = 10
            retention = 95
            marge = 30

    # ---------------------------
    # Appliquer les filtres RFM
    # ---------------------------
    df_filtered = df[df["Segment_RFM"].isin(segments_selected)]

    if df_filtered.empty:
        st.error("Aucun client dans les segments sélectionnés.")
        return

    # ---------------------------
    # Calculs du scénario
    # ---------------------------
    aov_new = df_filtered["Monetaire_Total_Depense"].mean() * (1 - remise / 100)
    freq_new = df_filtered["Frequence_Nb_Commandes"].mean()
    lifespan_new = lifespan * (retention / 100)

    clv_scenario = calculate_clv(aov_new, freq_new, lifespan_new)

    impact_pct = ((clv_scenario - clv_baseline) / clv_baseline) * 100

    # ---------------------------
    # KPI
    # ---------------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("CLV Baseline", f"{clv_baseline:,.2f} €")
    col2.metric("CLV Scénario", f"{clv_scenario:,.2f} €", delta=f"{clv_scenario - clv_baseline:,.2f} €")
    col3.metric("Impact (%)", f"{impact_pct:+.2f}%")

    # ---------------------------
    # GRAPHIQUE
    # ---------------------------
    st.subheader("📈 Sensibilité de la CLV au taux de rétention")

    retention_range = np.linspace(0.1, 0.99, 12)
    clv_sensitivity = [
        calculate_clv(aov_new, freq_new, lifespan * r)
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

    # ---------------------------
    # RÉCAPITULATIF
    # ---------------------------
    st.subheader("🧾 Tableau Récapitulatif des Paramètres")

    recap = pd.DataFrame({
        "Paramètre": [
            "Marge", "Remise", "Rétention", "Taux d'actualisation",
            "AOV recalculé", "Fréquence", "Durée de vie client (ans)"
        ],
        "Valeur": [
            f"{marge}%",
            f"{remise}%",
            f"{retention}%",
            f"{taux_actualisation}%",
            f"{aov_new:,.2f} €",
            f"{freq_new:,.2f}",
            f"{lifespan_new:,.2f} ans"
        ]
    })

    st.table(recap)

    # ---------------------------
    # EXPORTS
    # ---------------------------
    st.subheader("📤 Export des résultats")

    # Export CSV → clients filtrés
    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📄 Télécharger les données filtrées (CSV)",
        data=csv,
        file_name="clients_filtres.csv",
        mime="text/csv"
    )

    # Export HTML → graphique interactif
    html_graph = fig.to_html(full_html=False, include_plotlyjs="cdn")
    st.download_button(
        label="📊 Télécharger le graphique (HTML)",
        data=html_graph.encode("utf-8"),
        file_name="graphique_clv.html",
        mime="text/html"
    )


# Lancer la page
show_scenarios()
