import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Tableau de Bord Marketing - Scénarios",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def load_data():
    try:
        # Essayer deux chemins possibles pour le fichier
        try:
            df = pd.read_parquet("data/online_retail_clean.parquet")
        except:
            df = pd.read_parquet("data/processed/online_retail_clean.parquet")        
        # Renommer les colonnes si nécessaire
        if 'Customer ID' in df.columns:
            df = df.rename(columns={'Customer ID': 'CustomerID'})
        if 'Price' in df.columns:
            df = df.rename(columns={'Price': 'UnitPrice'})
        if 'Invoice' in df.columns:
            df = df.rename(columns={'Invoice': 'InvoiceNo'})
        
        # Créer la colonne Total si elle n'existe pas
        if 'Total' not in df.columns and all(col in df.columns for col in ['Quantity', 'UnitPrice']):
            df['Total'] = df['Quantity'] * df['UnitPrice']
        
        # Gestion des CustomerID manquants
        if 'CustomerID' not in df.columns or df['CustomerID'].isna().all():
            df['CustomerID'] = 'CUST_' + df.index.astype(str)
            st.warning("Aucun identifiant client trouvé. Des identifiants factices ont été générés.")
        
        # Créer les cohortes
        if 'InvoiceDate' in df.columns:
            df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
            df['Cohort'] = df['InvoiceDate'].dt.to_period('M').astype(str)
        else:
            df['Cohort'] = 'Toutes'
        
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

def show_scenarios():
    st.title("📈 Simulation d'Impact Marketing")
    st.markdown("Simulez l'impact de différentes stratégies marketing sur la CLV.")

    # Charger les données
    df = load_data()
    
    if df.empty:
        st.error("Impossible de charger les données. Vérifiez le fichier de données.")
        return

    
    with st.sidebar:
        st.header("Paramètres de Simulation")

        # Sélecteur de cohorte
        cohort_options = ["Toutes les cohortes"] + sorted(df["Cohort"].unique())
        cohort_select = st.selectbox("Cohorte cible", cohort_options)

        # Filtrage par cohorte
        if cohort_select != "Toutes les cohortes":
            df = df[df["Cohort"] == cohort_select]

        st.subheader("Paramètres financiers")
        marge = st.slider("Marge brute moyenne (%)", 0.0, 100.0, 30.0, 0.1)
        remise = st.slider("Remise moyenne (%)", 0.0, 100.0, 10.0, 0.1)

        remise_application = st.radio(
            "Appliquer la remise à :", 
            ["Tous les clients", "Segments spécifiques"]
        )
        
        if remise_application == "Segments spécifiques":
            segments = st.multiselect(
                "Choisir segments RFM :",
                df["RFM_Segment"].unique(),
                default=df["RFM_Segment"].unique()[:1] if len(df["RFM_Segment"].unique()) > 0 else []
            )
            if segments:
                df = df[df["RFM_Segment"].isin(segments)]

        st.subheader("Paramètres de rétention")
        retention_rate = st.slider("Taux de rétention (%)", 0.0, 100.0, 70.0, 0.1)
        
        st.subheader("Paramètres CLV")
        discount_rate = st.slider("Taux d'actualisation (%)", 0.0, 30.0, 10.0, 0.1)
        
        include_returns = st.checkbox("Inclure les retours", value=True)

    # Filtrage des retours si nécessaire
    if not include_returns and 'Quantity' in df.columns:
        df = df[df["Quantity"] > 0]

    # Calcul des métriques de base
    try:
        total_revenue = df["Total"].sum()
        avg_order_value = df["Total"].mean()
    except:
        st.error("Impossible de calculer les métriques financières. Vérifiez les colonnes 'Total' ou 'UnitPrice' et 'Quantity'.")
        return

    # Calcul des métriques avancées
    avg_purchase_freq = compute_avg_purchase_frequency(df)
    customer_lifespan = compute_customer_lifespan(df)

    # Conversion des pourcentages
    r_input = retention_rate / 100
    d_input = discount_rate / 100

    # Calcul de la CLV de base
    clv_baseline = calculate_clv(
        df, r_input, d_input, avg_order_value, 
        avg_purchase_freq, customer_lifespan, marge
    )

    # Calcul du scénario
    new_aov = avg_order_value * (1 - remise / 100)
    new_r = min(0.99, r_input + 0.05)  # On évite la division par zéro

    clv_scenario = calculate_clv(
        df, new_r, d_input, new_aov, 
        avg_purchase_freq, customer_lifespan, marge
    )

    # Affichage des KPI
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "CLV Actuelle", 
        f"{clv_baseline:,.2f} €",
        help=f"CLV calculée avec une marge de {marge}%"
    )

    col2.metric(
        "CLV Scénario",
        f"{clv_scenario:,.2f} €",
        delta=f"{(clv_scenario - clv_baseline):,.2f} €",
        delta_color="inverse" if clv_scenario < clv_baseline else "normal"
    )

    impact_pct = ((clv_scenario - clv_baseline) / clv_baseline * 100) if clv_baseline != 0 else 0
    col3.metric(
        "Impact sur la CLV", 
        f"{impact_pct:+.2f}%",
        help="Variation en pourcentage de la CLV"
    )

    # Graphique de sensibilité
    st.subheader("Sensibilité de la CLV au Taux de Rétention")
    
    retention_range = np.linspace(0.1, 0.99, 10)  # Éviter la division par zéro
    clv_values = [
        calculate_clv(
            df, r, d_input, new_aov, 
            avg_purchase_freq, customer_lifespan, marge
        )
        for r in retention_range
    ]

    fig = px.line(
        x=retention_range * 100,
        y=clv_values,
        labels={"x": "Taux de rétention (%)", "y": "CLV (€)"},
        markers=True,
        title="Impact du taux de rétention sur la CLV"
    )
    
    fig.add_hline(
        y=clv_baseline,
        line_dash="dash",
        line_color="red",
        annotation_text=f"CLV actuelle : {clv_baseline:,.2f} €",
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Récapitulatif
    st.subheader("Récapitulatif des Paramètres")

    summary = pd.DataFrame({
        "Paramètre": [
            "Cohorte sélectionnée",
            "Marge brute moyenne",
            "Remise appliquée",
            "Taux de rétention",
            "Taux d'actualisation",
            "Retours inclus",
            "Application de remise",
            "Fréquence d'achat moyenne (par mois)",
            "Durée de vie moyenne (années)"
        ],
        "Valeur": [
            cohort_select,
            f"{marge}%",
            f"{remise}%",
            f"{retention_rate}%",
            f"{discount_rate}%",
            "Oui" if include_returns else "Non",
            remise_application,
            f"{avg_purchase_freq:.2f}",
            f"{customer_lifespan:.2f}"
        ]
    })

    st.table(summary)

    # Bouton d'export
    if st.button("Exporter les Résultats"):
        export_data = {
            "Métrique": ["CLV Actuelle", "CLV Scénario", "Impact (€)", "Impact (%)"],
            "Valeur": [
                f"{clv_baseline:,.2f} €",
                f"{clv_scenario:,.2f} €",
                f"{(clv_scenario - clv_baseline):,.2f} €",
                f"{impact_pct:+.2f}%"
            ]
        }
        
        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="Télécharger les résultats en CSV",
            data=csv,
            file_name=f"simulation_clv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv',
        )

if __name__ == "__main__":
    show_scenarios()