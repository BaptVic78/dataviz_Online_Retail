import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime
from io import BytesIO
import io

@st.cache_data
def load_data():
    try:
        df = pd.read_parquet("data/processed/online_retail_clean.parquet")
       
        # Renommer les colonnes si nécessaire
        if 'Customer ID' in df.columns:
            df = df.rename(columns={'Customer ID': 'CustomerID'})
        if 'Price' in df.columns:
            df = df.rename(columns={'Price': 'UnitPrice'})
        if 'Invoice' in df.columns:
            df = df.rename(columns={'Invoice': 'InvoiceNo'})
    
        
        # Créer des segments RFM factices si nécessaire
        if 'RFM_Segment' not in df.columns:
            df['RFM_Segment'] = 'Aucun segment'
        
        return df
        
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        return pd.DataFrame()

def compute_avg_purchase_frequency(df):
    """Calcule la fréquence moyenne d'achat"""
    if 'CustomerID' not in df.columns or 'InvoiceDate' not in df.columns:
        return 12  # Valeur par défaut
    try:
        df_dates = df.groupby("CustomerID")["InvoiceDate"].agg(["min", "max", "count"])
        df_dates["active_months"] = ((df_dates["max"] - df_dates["min"]) / np.timedelta64(30, "D")).clip(lower=1)
        df_dates["freq"] = df_dates["count"] / df_dates["active_months"]
        return df_dates["freq"].mean()
    except:
        return 12  # Valeur par défaut en cas d'erreur

def compute_customer_lifespan(df):
    """Calcule la durée de vie moyenne des clients en années"""
    if 'CustomerID' not in df.columns or 'InvoiceDate' not in df.columns:
        return 3  # Valeur par défaut
    try:
        span = df.groupby("CustomerID")["InvoiceDate"].agg(["min", "max"])
        lifespan_days = (span["max"] - span["min"]).dt.days.clip(lower=1)
        return lifespan_days.mean() / 365
    except:
        return 3  # Valeur par défaut en cas d'erreur

def calculate_clv(df, r, d, aov, freq, lifespan, marge=30.0):
    """Calcule la CLV avec marge brute"""
    if r <= 0 or d <= 0:
        return 0
    try:
        aov_with_margin = aov * (marge / 100)
        clv = (aov_with_margin * freq * r) / (1 + d - r)
        return clv * lifespan
    except:
        return 0
    
#Calcul de la tables des pivots pour afficher la heatmap
@st.cache_data
def compute_cohort_matrix(df):
    cohort_counts = df.groupby(['Cohort', 'CohortIndex'])['CustomerID'].nunique()
    cohort_counts_df = cohort_counts.to_frame().rename(columns={'CustomerID' : 'Total Customers'}).sort_values(by='Total Customers', ascending=False)
    cohort_counts_df['retention_rate'] = cohort_counts_df['Total Customers'] / cohort_counts_df.groupby(['Cohort'])['Total Customers'].transform('max')
    cohorts_pivot = cohort_counts_df.pivot_table(index='Cohort', columns='CohortIndex', values='retention_rate') 
    return cohorts_pivot

def plot_retention_heatmap(cohorts_pivot):
    fig, ax = plt.subplots(figsize=(20, 10))

    with plt.style.context('dark_background'):
        sns.heatmap(data=cohorts_pivot, 
            annot=True, 
            fmt='.0%', 
            cmap='Blues', 
            vmin=0.0,
            vmax=0.5,
            ax=ax
        )
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        ax.set_title('Heatmap des taux de rétention par cohortes', fontsize=16, color='white')
        ax.set_xlabel('Mois depuis l\'acquisition', fontsize=14)
        ax.set_ylabel('Cohorte d\'acquisition', fontsize=14)
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        cbar = ax.collections[0].colorbar
        cbar.ax.tick_params(colors='white')

    st.pyplot(fig, transparent=True, use_container_width=True)

    add_download_button(fig, filename="heatmap_retention.png")

    with st.expander("où investir, où réduire les dépenses", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Ou investir")
            st.success(
                """
                La heatmap montre les cohortes qui restent bleues longtemps (clients fidèles)
                Il faut garder ces clients car il "répondent"
                """
            )
        
        with col2:
            st.markdown("### segments/cohortes qui répondent")
            st.error(
                """
                La heatmap montre les cohortes qui deviennent blanches tout de suite
                Il faut réduire les dépenses sur ces cohortes car ils ne "répondent pas"
                """
            )

# Ce graphe sert à analyser le panier type des clients en fonction de leur âge de cohorte 
# on pourra observer qu'un client ancien a un panier moyen plus élevé qu'un clien récent
def densite(df):
    st.subheader("Analyse de la densité")
    
    subset = subset = df[(df['TotalPrice'] > 0) & (df['TotalPrice'] < 75)]

    all_ages = sorted(subset['CohortIndex'].unique()) #on recupère tous les âges de cohortes (0 à 24)

    with st.expander("🔽 Filtres", expanded=True):
        selected_cohorts = st.multiselect(
            "Sélectionner les âges (Mois) à comparer :",
            options=all_ages,
            default=all_ages[:5] # On en limite 5 par défaut pour la lisibilité
        )

    if not selected_cohorts:
        st.warning("Sélectionnez au moins un âge.")
        return
    
    plot_data = subset[subset['CohortIndex'].isin(selected_cohorts)]

    if len(plot_data) > 10000:
        plot_data = plot_data.sample(n=10000, random_state=42)

    fig, ax = plt.subplots(figsize=(10, 6))

    with plt.style.context('dark_background'):
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        sns.kdeplot(
            data=plot_data,
            x='TotalPrice',    
            hue='CohortIndex',   
            fill=True,         
            common_norm=False,  
            palette='viridis',
            alpha=0.3,
            linewidth=1.5,
            ax=ax,
            warn_singular=False
        ) 
        ax.set_title('courbes de densité de CA par age de cohorte', fontsize=16, color='white')
        ax.set_xlabel('Total du CA', fontsize=14)
        ax.set_ylabel('Densité', fontsize=14)
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        if ax.legend_:
            plt.setp(ax.get_legend().get_texts(), color='white')

    st.pyplot(fig, transparent=True, use_container_width=True)

    add_download_button(fig, filename="densite_ca_par_age.png")

    with st.expander("Interprétation", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📉 Points de Vigilance")
            st.warning(
                """
                **1. Décrochage structurel (M+1) :** Environ **75% à 80%** des clients ne reviennent pas après leur premier achat. 
                L'effort de rétention doit se concentrer sur l'onboarding immédiat.
                """
            )
            st.error(
                """
                **2. Alerte Qualité (Déc 2010) :** La cohorte de **2010-12** montre une performance catastrophique 
                (**12%** de rétention à M+1 contre **38%** l'année précédente).
                *Hypothèse : Acquisition de mauvaise qualité (chasseurs de primes de Noël).*
                """
            )
        
        with col2:
            st.markdown("### 📈 Signaux Positifs")
            st.success(
                """
                **3. Fidélité "Saisonnière" (Effet Anniversaire) :** La cohorte de **2009-12** remonte spectaculairement à **50% de rétention** en Novembre 2010 (M+11).  
                Cela indique une base de clients fidèles à la marque pour les achats de fin d'année.
                """
            )
            st.info(
                """
                **4. Noyau Dur :** Passé le cap des 3 mois, la rétention se stabilise autour de **20-25%**.
                Ces clients constituent la base saine et récurrente du chiffre d'affaires.
                """
            )

def plot_retention_curves(cohorts_pivot):
    st.subheader("📉 Courbes de Rétention par Cohorte")
    
    # On transpose pour avoir les mois (0, 1, 2...) en axe X
    # et les cohortes en différentes lignes
    df_plot = cohorts_pivot.T
    
    fig = px.line(
        df_plot, 
        markers=True,
        title="Comparaison des trajectoires de rétention",
        labels={"index": "Mois après acquisition", "value": "Taux de Rétention"}
    )
    
    fig.update_layout(yaxis_tickformat=".0%") # Axe Y en %
    st.plotly_chart(fig, use_container_width=True)

def plot_average_retention(cohorts_pivot):
    st.subheader("⚖️ Rétention Moyenne Globale")
    
    # On calcule la moyenne de chaque colonne (M0, M1, M2...)
    avg_retention = cohorts_pivot.iloc[:, 1:].mean(axis=0)
    
    fig = px.area(
        x=avg_retention.index, 
        y=avg_retention.values,
        title="Courbe de vie moyenne d'un client",
        labels={"x": "Mois d'ancienneté", "y": "Taux moyen de présence"},
        markers=True
    )
    
    fig.update_layout(yaxis_tickformat=".0%")
    # Ajout d'une ligne seuil à 20% 
    fig.add_hline(y=0.20, line_dash="dot", annotation_text="Seuil de fidélité (20%)")
    
    st.plotly_chart(fig, use_container_width=True)


# ============================
# 📌 CHARGEMENT DES DONNÉES
# ============================
def load_rfm(path="data/processed/df_rfm_resultat.csv"):
    df = pd.read_csv(path)
    df['Customer ID'] = df['Customer ID'].astype(int)
    df['Date_Premier_Achat'] = pd.to_datetime(df['Date_Premier_Achat'])
    return df


# ============================
# 📌 SEGMENTATION RFM
# ============================
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


def add_rfm_segment(df):
    df['Segment'] = df['RFM_Pourcentage'].apply(assign_segment)
    priority_mapping = {
        "Champions": 1,
        "Fidèles": 2,
        "Potentiels": 3,
        "À Risque": 4,
        "Perdus": 5
    }
    df['Priorite'] = df['Segment'].map(priority_mapping)
    return df


# ============================
# 📌 AGRÉGATS PAR SEGMENT
# ============================
def compute_segment_table(df, taux_marge):
    seg = df.groupby(['Segment', 'Priorite'], as_index=False).agg(
        Volume_clients=('Customer ID', 'nunique'),
        CA=('Monetaire_Total_Depense', 'sum'),
        Panier_moyen=('Monetaire_Total_Depense', 'mean')
    )
    seg['Marge'] = seg['CA'] * taux_marge
    return seg.sort_values('Priorite')


def format_segment_table(seg, df):
    display_df = seg[['Segment', 'Volume_clients', 'CA', 'Marge', 'Panier_moyen', 'Priorite']].copy()

    blank_row = pd.DataFrame({
        'Segment': [''],
        'Volume_clients': [''],
        'CA': [''],
        'Marge': [''],
        'Panier_moyen': [''],
        'Priorite': ['']
    })

    total_row = pd.DataFrame({
        'Segment': ['TOTAL'],
        'Volume_clients': [df['Customer ID'].nunique()],
        'CA': [seg['CA'].sum()],
        'Marge': [seg['Marge'].sum()],
        'Panier_moyen': [''],
        'Priorite': ['']
    })

    display_df = pd.concat([display_df, blank_row, total_row], ignore_index=True)

    # Formatage
    for col in ['CA', 'Marge', 'Panier_moyen']:
        display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
        display_df[col] = display_df[col].round(2)
        display_df[col] = display_df[col].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

    return display_df


# ============================
# 📌 CALCUL DES SCÉNARIOS
# ============================
def compute_scenario(seg_row, taux_marge, part_clients, uplift_ca):
    ca_base = seg_row['CA']
    marge_base = seg_row['Marge']

    part_dec = part_clients / 100
    uplift_dec = uplift_ca / 100

    ca_incremental = ca_base * part_dec * uplift_dec
    marge_incrementale = ca_incremental * taux_marge
    ca_nouveau = ca_base + ca_incremental
    marge_nouvelle = marge_base + marge_incrementale

    return {
        "ca_base": ca_base,
        "ca_incremental": ca_incremental,
        "ca_nouveau": ca_nouveau,
        "marge_base": marge_base,
        "marge_incrementale": marge_incrementale,
        "marge_nouvelle": marge_nouvelle
    }


# ============================
# 📌 GRAPHIQUE + EXPORT
# ============================
def plot_scenario_chart(ca_base, ca_incremental):
    ca_base_k = ca_base / 1000
    ca_inc_k = ca_incremental / 1000

    fig, ax = plt.subplots(figsize=(4, 4))

    ax.bar(["Scénario"], [ca_base_k], label="CA base", color="#4e79a7")
    ax.bar(["Scénario"], [ca_inc_k], bottom=[ca_base_k], label="CA additionnel", color="#f28e2b")

    total = ca_base_k + ca_inc_k

    ax.set_ylabel("CA (k€)")
    ax.set_ylim(0, total * 1.25)
    ax.legend()

    ax.text(0, total, f"{total:,.0f} k€", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.ticklabel_format(style='plain', axis='y')

    return fig


def export_figure_png(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    return buffer

def add_download_button(fig, filename="graphique.png"):
    """Ajoute un bouton de téléchargement pour une figure Matplotlib"""
    # 1. Sauvegarder l'image dans un buffer (mémoire vive)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, transparent=True)
    buf.seek(0)
    
    # 2. Créer le bouton Streamlit
    st.download_button(
        label="📸 Télécharger ce graphique (PNG)",
        data=buf,
        file_name=filename,
        mime="image/png",
        key=filename # Clé unique importante si plusieurs boutons sur la page
    )