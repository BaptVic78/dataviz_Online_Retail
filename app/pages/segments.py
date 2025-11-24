import streamlit as st
import pandas as pd
import numpy as np

# --- Config page ---
st.set_page_config(
    page_title="RFM - Online Retail",
    layout="wide"
)

st.title("Tableau de bord RFM - Clients & Scénarios CRM")

# --- Chargement des données ---
@st.cache_data
def load_rfm():
    df = pd.read_csv("data/processed/df_rfm_resultat.csv")
    return df

df_rfm = load_rfm()

# --- Sécurité : conversion des colonnes clés ---
df_rfm['Customer ID'] = df_rfm['Customer ID'].astype(int)
df_rfm['Date_Premier_Achat'] = pd.to_datetime(df_rfm['Date_Premier_Achat'])

# --- Construction des segments RFM ---
def assign_segment(row):
    r = row['R_Score']
    f = row['F_Score']
    m = row['M_Score']

    if (r >= 4) and (f >= 4) and (m >= 4):
        return "Champions"
    elif (r >= 4) and (f >= 3):
        return "Clients fidèles"
    elif (r == 5) and (f <= 2):
        return "Nouveaux clients"
    elif (r <= 2) and (f >= 3):
        return "À risque"
    elif (r <= 2) and (f <= 2):
        return "Perdus"
    else:
        return "Potentiel"

df_rfm['Segment'] = df_rfm.apply(assign_segment, axis=1)

# --- Priorité d'activation ---
priority_mapping = {
    "Champions": 1,
    "À risque": 2,
    "Clients fidèles": 3,
    "Potentiel": 4,
    "Nouveaux clients": 5,
    "Perdus": 6
}
df_rfm['Priorite'] = df_rfm['Segment'].map(priority_mapping)

# --- Paramètres de marge (sidebar) ---
st.sidebar.header("Paramètres business")
taux_marge = st.sidebar.slider(
    "Taux de marge (%)",
    min_value=0,
    max_value=100,
    value=30,
    step=1
) / 100

# --- Agrégats par segment ---
seg_table = df_rfm.groupby(['Segment', 'Priorite'], as_index=False).agg(
    Volume_clients=('Customer ID', 'nunique'),
    CA=('Monetaire_Total_Depense', 'sum'),
    Panier_moyen=('Monetaire_Total_Depense', 'mean')
)

seg_table['Marge'] = seg_table['CA'] * taux_marge

seg_table = seg_table.sort_values('Priorite')

# --- Affichage table RFM agrégée ---
st.subheader("Table RFM par segment")

st.dataframe(
    seg_table[['Segment', 'Volume_clients', 'CA', 'Marge', 'Panier_moyen', 'Priorite']],
    use_container_width=True
)

# --- KPIs globaux ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("CA total", f"{seg_table['CA'].sum():,.0f}")
with col2:
    st.metric("Marge totale", f"{seg_table['Marge'].sum():,.0f}")
with col3:
    st.metric("Nb clients", int(df_rfm['Customer ID'].nunique()))

# --- Bloc Scénarios / Simulation ---
st.markdown("---")
st.subheader("Scénarios CRM - Simulation d'activation")

col_seg, col_p, col_u = st.columns(3)

with col_seg:
    segment_cible = st.selectbox(
        "Segment ciblé",
        options=seg_table['Segment'].unique()
    )

with col_p:
    part_clients = st.slider(
        "Part de clients activés dans ce segment (%)",
        min_value=0,
        max_value=100,
        value=50,
        step=5
    )

with col_u:
    uplift_ca = st.slider(
        "Uplift de CA par client activé (%)",
        min_value=0,
        max_value=200,
        value=20,
        step=5
    )

# --- Calcul scénario ---
seg_row = seg_table[seg_table['Segment'] == segment_cible].iloc[0]

ca_base = seg_row['CA']
marge_base = seg_row['Marge']
nb_clients_seg = seg_row['Volume_clients']

part_clients_dec = part_clients / 100
uplift_dec = uplift_ca / 100

ca_incremental = ca_base * part_clients_dec * uplift_dec
marge_incrementale = ca_incremental * taux_marge

ca_nouveau = ca_base + ca_incremental
marge_nouvelle = marge_base + marge_incrementale

st.markdown(f"### Résultats pour le segment **{segment_cible}**")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric(
        "CA segment (base)",
        f"{ca_base:,.0f}"
    )
with c2:
    st.metric(
        "CA additionnel simulé",
        f"{ca_incremental:,.0f}"
    )
with c3:
    st.metric(
        "CA nouveau (base + scénar.)",
        f"{ca_nouveau:,.0f}"
    )

d1, d2 = st.columns(2)
with d1:
    st.metric(
        "Marge segment (base)",
        f"{marge_base:,.0f}"
    )
with d2:
    st.metric(
        "Marge additionnelle simulée",
        f"{marge_incrementale:,.0f}"
    )

st.caption(
    "Logique : CA_additionnel = CA_segment × part_clients_activés × uplift_CA ; "
    "Marge_additionnelle = CA_additionnel × taux de marge."
)
