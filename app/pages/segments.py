import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


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
    score = row['RFM_Pourcentage']

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

df_rfm['Segment'] = df_rfm.apply(assign_segment, axis=1)

# --- Priorité d'activation ---
priority_mapping = {
    "Champions": 1,
    "Fidèles": 2,
    "Potentiels": 3,
    "À Risque": 4,
    "Perdus": 5
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

# On prépare le tableau à afficher
display_df = seg_table[['Segment', 'Volume_clients', 'CA', 'Marge', 'Panier_moyen', 'Priorite']].copy()

# --- Ligne vide ---
blank_row = pd.DataFrame({
    'Segment': [''],
    'Volume_clients': [''],
    'CA': [''],
    'Marge': [''],
    'Panier_moyen': [''],
    'Priorite': ['']
})

# --- Ligne TOTAL ---
total_row = pd.DataFrame({
    'Segment': ['TOTAL'],
    'Volume_clients': [df_rfm['Customer ID'].nunique()],      # nb total de clients
    'CA': [seg_table['CA'].sum()],                            # CA total
    'Marge': [seg_table['Marge'].sum()],                      # Marge totale
    'Panier_moyen': [''],                                     # tu peux mettre un global si tu veux
    'Priorite': ['']
})

# On concatène : segments + ligne vide + total
display_df = pd.concat([display_df, blank_row, total_row], ignore_index=True)

# --- Affichage table RFM agrégée ---
st.subheader("Table RFM par segment")

# Colonnes numériques à formatter
num_cols = ['CA', 'Marge', 'Panier_moyen']

for col in num_cols:
    # Convertir en numérique (en gardant les NaN pour la ligne vide)
    display_df[col] = pd.to_numeric(display_df[col], errors='coerce')

    # Arrondir à 2 décimales
    display_df[col] = display_df[col].round(2)

    # Appliquer le format 3,994,348.18
    display_df[col] = display_df[col].map(
        lambda x: f"{x:,.2f}" if pd.notnull(x) else ""
    )


st.dataframe(
    display_df,
    use_container_width=True
)


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
# On récupère la ligne du segment ciblé
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


# --- Camembert CA base vs CA additionnel ---
st.subheader("Répartition du CA (base vs additionnel)")

labels = ["CA base", "CA additionnel simulé"]
values = [ca_base, ca_incremental]

# Taille du graphique réduite
fig, ax = plt.subplots(figsize=(3, 4))  # <-- DIMENSION ICI

ax.pie(
    values,
    labels=labels,
    autopct='%1.1f%%',
    startangle=90
)
ax.axis('equal')

st.pyplot(fig)


st.caption(
    "Logique : CA_additionnel = CA_segment × part_clients_activés × uplift_CA ; "
    "Marge_additionnelle = CA_additionnel × taux de marge."
)
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
