import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------------------------------------
# CONFIG PAGE
# ------------------------------------------------
st.set_page_config(
    page_title="Scénarios Marketing – CLV",
    page_icon="📈",
    layout="wide",
)

# ------------------------------------------------
# CSS GLOBAL (repris EXACTEMENT du thème principal)
# ------------------------------------------------
st.markdown("""
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
""", unsafe_allow_html=True)

# ------------------------------------------------
# KPI card helper
# ------------------------------------------------
def _kpi(label, value):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """

# ------------------------------------------------
# LOAD DATA
# ------------------------------------------------
@st.cache_data
def load_rfm():
    df = pd.read_csv("data/processed/df_rfm_resultat.csv")
    df["Date_Premier_Achat"] = pd.to_datetime(df["Date_Premier_Achat"])
    return df

def label_rfm(percent):
    if percent >= 400: return "Champions"
    elif percent >= 300: return "Fidèles"
    elif percent >= 200: return "Potentiels"
    elif percent >= 120: return "À Risque"
    else: return "Perdus"

def calculate_clv(aov, freq, lifespan_years):
    return aov * freq * lifespan_years

def compute_lifespan_years(df):
    days = (pd.Timestamp.today() - df["Date_Premier_Achat"]).dt.days
    return (days / 365).mean()


# ------------------------------------------------
# PAGE LOGIC
# ------------------------------------------------
def show_scenarios():

    # ------------------------------------------------
    # HEADER PAGE
    # ------------------------------------------------
    st.markdown("""
    <div class="section-bubble">
        <div class="section-header">
            <div class="section-pill">Analyse</div>
            <div class="section-title">📈 Simulation d'Impact Marketing (CLV)</div>
        </div>
        <p style='color:#9ca3af'>Analyse l'effet d'une remise, de la marge et de la rétention sur la valeur vie client.</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_rfm()
    df["Segment_RFM"] = df["RFM_Pourcentage"].apply(label_rfm)

    # ---------------------------
    # BASE METRICS
    # ---------------------------
    aov = df["Monetaire_Total_Depense"].mean()
    freq = df["Frequence_Nb_Commandes"].mean()
    lifespan = compute_lifespan_years(df)

    clv_baseline = calculate_clv(aov, freq, lifespan)

    # ------------------------------------------------
    # SIDEBAR
    # ------------------------------------------------
    with st.sidebar:
        st.header("⚙️ Paramètres du scénario")

        marge = st.slider("Marge brute (%)", 0.0, 100.0, 30.0)
        remise = st.slider("Remise (%)", 0.0, 80.0, 10.0)
        retention = st.slider("Taux de rétention (%)", 0.0, 100.0, 70.0)
        taux_actualisation = st.slider("Taux d'actualisation (%)", 0.0, 30.0, 10.0)

        segments_selected = st.multiselect(
            "🎯 Segments ciblés",
            df["Segment_RFM"].unique(),
            default=df["Segment_RFM"].unique().tolist()
        )

    df_filtered = df[df["Segment_RFM"].isin(segments_selected)]

    if df_filtered.empty:
        st.error("Aucun client dans cette sélection.")
        return

    # ------------------------------------------------
    # SCENARIO CALCUL
    # ------------------------------------------------
    aov_new = df_filtered["Monetaire_Total_Depense"].mean() * (1 - remise/100)
    freq_new = df_filtered["Frequence_Nb_Commandes"].mean()
    lifespan_new = lifespan * (retention/100)

    clv_scenario = calculate_clv(aov_new, freq_new, lifespan_new)
    impact_pct = ((clv_scenario - clv_baseline) / clv_baseline) * 100

    # ------------------------------------------------
    # KPI BUBBLE
    # ------------------------------------------------
    st.markdown("""
    <div class="section-bubble">
        <div class="section-header">
            <div class="section-pill">Synthèse</div>
            <div class="section-title">📌 Indicateurs CLV</div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.markdown(_kpi("CLV Baseline", f"{clv_baseline:,.2f} €"), unsafe_allow_html=True)
    c2.markdown(_kpi("CLV Scénario", f"{clv_scenario:,.2f} €"), unsafe_allow_html=True)
    c3.markdown(_kpi("Impact (%)", f"{impact_pct:+.2f}%"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------
    # SENSITIVITY CURVE
    # ------------------------------------------------
    st.markdown("""
    <div class="section-bubble">
        <div class="section-header">
            <div class="section-pill">Analyse</div>
            <div class="section-title">📉 Sensibilité au taux de rétention</div>
        </div>
    """, unsafe_allow_html=True)

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
    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------
    # SUMMARY TABLE
    # ------------------------------------------------
    st.markdown("""
    <div class="section-bubble">
        <div class="section-header">
            <div class="section-pill">Synthèse</div>
            <div class="section-title">🧾 Récapitulatif</div>
        </div>
    """, unsafe_allow_html=True)

    recap = pd.DataFrame({
        "Paramètre": ["Marge", "Remise", "Rétention", "Taux d'actualisation",
                      "AOV recalculé", "Fréquence", "Durée de vie client"],
        "Valeur": [f"{marge}%", f"{remise}%", f"{retention}%", f"{taux_actualisation}%",
                   f"{aov_new:,.2f} €", f"{freq_new:,.2f}", f"{lifespan_new:,.2f} ans"]
    })
    st.table(recap)

    st.markdown("</div>", unsafe_allow_html=True)


# RUN PAGE
show_scenarios()
