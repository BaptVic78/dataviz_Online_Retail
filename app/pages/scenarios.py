import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Scénarios CLV – RFM", layout="wide")
st.title("Scénarios CLV par segment – remise, marge, rétention")

# ----------------- DONNÉES RFM -----------------
@st.cache_data
def load_rfm():
    df = pd.read_csv("data/processed/df_rfm_resultat.csv")
    df["Customer ID"] = df["Customer ID"].astype(int)
    return df

df = load_rfm()

# Si le segment n'est pas déjà dans le CSV, on le reconstruit depuis RFM_Pourcentage
def assign_segment(score):
    if score >= 400:
        return "Champions"
    elif 300 <= score <= 399:
        return "Fidèles"
    elif 200 <= score <= 299:
        return "Potentiels"
    elif 120 <= score <= 199:
        return "À Risque"
    else:
        return "Perdus"

if "Segment" not in df.columns:
    df["Segment"] = df["RFM_Pourcentage"].apply(assign_segment)

# AOV (panier moyen par client)
df["AOV"] = df["Monetaire_Total_Depense"] / df["Frequence_Nb_Commandes"]

# ----------------- FILTRE SEGMENT -----------------
segments = sorted(df["Segment"].unique())
segment_cible = st.selectbox("Segment de clients", options=segments)

df_seg = df[df["Segment"] == segment_cible].copy()

if df_seg.empty:
    st.error("Aucun client dans ce segment.")
    st.stop()

nb_clients = df_seg["Customer ID"].nunique()
aov_seg = (df_seg["Monetaire_Total_Depense"].sum() /
           df_seg["Frequence_Nb_Commandes"].sum())
freq_seg = df_seg["Frequence_Nb_Commandes"].mean()

st.markdown(
    f"""
    ### 📊 Profil du segment **{segment_cible}**
    - Nombre de clients : **{nb_clients}**
    - Panier moyen (AOV) : **{aov_seg:,.2f} €**
    - Nombre moyen de commandes (période observée) : **{freq_seg:,.2f}**
    """
)

# ----------------- PARAMÈTRES BUSINESS -----------------
st.markdown("---")
st.subheader("Paramètres business et scénario")

col_base, col_scen = st.columns(2)

with col_base:
    st.markdown("#### Baseline")
    marge_base_pct = st.slider("Marge brute baseline (%)", 5, 80, 30, 1)
    r_base_pct = st.slider("Rétention baseline (%)", 10, 95, 60, 1)
    d_pct = st.slider("Taux d'actualisation (%)", 0, 30, 10, 1)

with col_scen:
    st.markdown("#### Scénario")
    remise_pct = st.slider("Remise moyenne accordée (%)", 0, 70, 10, 1)
    gain_retention_pts = st.slider(
        "Gain de rétention (points de %)",
        min_value=0,
        max_value=40,
        value=5,
        step=1,
    )
    delta_marge_pts = st.slider(
        "Variation de marge (points de %)",
        min_value=-30,
        max_value=30,
        value=-5,
        step=1,
    )

# ----------------- FONCTION CLV -----------------
def calculate_clv(aov, freq, retention_pct, discount_pct, marge_pct):
    """CLV = marge_par_période * r / (1 + d - r)"""
    r = retention_pct / 100
    d = discount_pct / 100
    marge = marge_pct / 100

    if r <= 0:
        return 0.0

    profit_par_periode = aov * marge * freq
    try:
        clv = (profit_par_periode * r) / (1 + d - r)
        return max(clv, 0.0)
    except ZeroDivisionError:
        return 0.0

# ----------------- CALCUL BASELINE VS SCÉNARIO -----------------
# Baseline
clv_base = calculate_clv(
    aov=aov_seg,
    freq=freq_seg,
    retention_pct=r_base_pct,
    discount_pct=d_pct,
    marge_pct=marge_base_pct,
)
ca_base = aov_seg * freq_seg  # CA par client (période)

# Scénario
aov_scen = aov_seg * (1 - remise_pct / 100)
r_scen_pct = min(r_base_pct + gain_retention_pts, 99)
marge_scen_pct = marge_base_pct + delta_marge_pts

clv_scen = calculate_clv(
    aov=aov_scen,
    freq=freq_seg,
    retention_pct=r_scen_pct,
    discount_pct=d_pct,
    marge_pct=marge_scen_pct,
)
ca_scen = aov_scen * freq_seg

delta_clv = clv_scen - clv_base
delta_ca = ca_scen - ca_base
delta_r = r_scen_pct - r_base_pct

# ----------------- COMPARAISON BARRES + DELTAS -----------------
st.markdown("---")
st.subheader("Comparaison baseline vs scénario")

col_g, col_m = st.columns([2, 1])

with col_g:
    labels = ["CLV (€)", "CA / client"]
    baseline_vals = [clv_base, ca_base]
    scen_vals = [clv_scen, ca_scen]

    x = [0, 1]
    width = 0.35

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar([i - width/2 for i in x], baseline_vals, width, label="Baseline")
    ax.bar([i + width/2 for i in x], scen_vals, width, label="Scénario")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Valeur")
    ax.legend()
    ax.ticklabel_format(style="plain", axis="y")

    st.pyplot(fig)

with col_m:
    st.metric("CLV baseline", f"{clv_base:,.0f} €")
    st.metric("CLV scénario", f"{clv_scen:,.0f} €")
    st.metric("Δ CLV par client", f"{delta_clv:,.0f} €")
    st.markdown("---")
    st.metric("CA baseline", f"{ca_base:,.0f} €")
    st.metric("CA scénario", f"{ca_scen:,.0f} €")
    st.metric("Δ CA par client", f"{delta_ca:,.0f} €")
    st.markdown("---")
    st.metric("Rétention baseline", f"{r_base_pct:.1f} %")
    st.metric("Rétention scénario", f"{r_scen_pct:.1f} %")
    st.metric("Δ rétention", f"{delta_r:.1f} points")

# ----------------- COURBE : CLV EN FONCTION DU GAIN DE RÉTENTION -----------------
st.markdown("---")
st.subheader("Courbe : CLV en fonction du gain de rétention")

gain_max = st.slider(
    "Gain de rétention max testé (points de %)",
    min_value=5,
    max_value=50,
    value=30,
    step=5,
)

gains = list(range(0, gain_max + 1, 5))
clv_vals = []

for g in gains:
    r_tmp = min(r_base_pct + g, 99)
    clv_tmp = calculate_clv(
        aov=aov_scen,
        freq=freq_seg,
        retention_pct=r_tmp,
        discount_pct=d_pct,
        marge_pct=marge_scen_pct,
    )
    clv_vals.append(clv_tmp)

fig2, ax2 = plt.subplots(figsize=(6, 4))
ax2.plot(gains, clv_vals, marker="o")
ax2.set_xlabel("Gain de rétention (points de %)")
ax2.set_ylabel("CLV scénario (€)")
ax2.grid(True)
ax2.ticklabel_format(style="plain", axis="y")
st.pyplot(fig2)

# ----------------- PLAN D'ACTION (EXPORT) -----------------
st.markdown("---")
st.subheader("Plan d’action (export)")

plan = f"""
PLAN D'ACTION – SEGMENT {segment_cible}

Hypothèses segment :
- Nombre de clients : {nb_clients}
- Panier moyen (AOV) : {aov_seg:,.2f} €
- Nombre moyen de commandes : {freq_seg:,.2f}

Paramètres baseline :
- Marge : {marge_base_pct:.1f} %
- Rétention : {r_base_pct:.1f} %
- Taux d'actualisation : {d_pct:.1f} %
- CLV baseline : {clv_base:,.2f} € / client
- CA baseline : {ca_base:,.2f} € / client

Paramètres scénario :
- Remise : {remise_pct:.1f} %
- Gain de rétention : +{gain_retention_pts:.1f} points (→ {r_scen_pct:.1f} %)
- Variation de marge : {delta_marge_pts:+.1f} points (→ {marge_scen_pct:.1f} %)
- CLV scénario : {clv_scen:,.2f} € / client
- CA scénario : {ca_scen:,.2f} € / client

Impacts (par client du segment) :
- Δ CLV : {delta_clv:,.2f} €
- Δ CA : {delta_ca:,.2f} €
- Δ rétention : {delta_r:,.1f} points

Si tu cibles tous les {nb_clients} clients du segment :
- Gain total CLV estimé : {delta_clv * nb_clients:,.2f} €
- Gain total de CA estimé (une période) : {delta_ca * nb_clients:,.2f} €
"""

buf = BytesIO(plan.encode("utf-8"))

st.download_button(
    label="📥 Télécharger le plan d’action (TXT)",
    data=buf,
    file_name=f"plan_action_{segment_cible}.txt",
    mime="text/plain",
)
